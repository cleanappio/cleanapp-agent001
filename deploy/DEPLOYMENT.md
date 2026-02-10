# Deployment Guide — CleanApp Agent001

This guide describes how to deploy the agent to **Google Cloud Run** in a locked-down, secure environment.

## Prerequisites

- Google Cloud Project
- `gcloud` CLI installed and authenticated
- Docker installed

## 1. Setup Environment

Set your project variables:

```bash
export PROJECT_ID="cleanapp-agent-001"  # Recommended: Dedicated project
export REGION="us-central1"
export SERVICE_NAME="cleanapp-agent"
export SERVICE_ACCOUNT="cleanapp-agent-sa@${PROJECT_ID}.iam.gserviceaccount.com"
```

## 2. Create Service Account

Create a dedicated service account with minimal permissions:

```bash
# Create SA
gcloud iam service-accounts create cleanapp-agent-sa \
    --display-name="CleanApp Agent Service Account"

# Allow SA to access Secret Manager (needed for keys)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

## 3. Configure Secrets

Store your API keys in Secret Manager. Do NOT put them in env vars directly.

```bash
# Enable Secret Manager
gcloud services enable secretmanager.googleapis.com

# Create secrets
printf "moltbook_xxx" | gcloud secrets create moltbook-api-key --data-file=-
printf "your_gemini_key" | gcloud secrets create gemini-api-key --data-file=-
```

## 4. Build and Push Container

```bash
# Enable Artifact Registry
gcloud services enable artifactregistry.googleapis.com

# Create repository
gcloud artifacts repositories create cleanapp-repo \
    --repository-format=docker \
    --location=${REGION}

# Build and push
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/cleanapp-repo/${SERVICE_NAME}:latest
```

## 5. Deploy to Cloud Run

Deploy as a **job** (since it runs a loop and sleeps) or a **service** (if triggered). For a continuous agent loop, use a **Job** with a timeout or a Service with min-instances=1.

Here is the configuration for a **Cloud Run Job** (best for batch/loop execution):

```bash
gcloud run jobs create ${SERVICE_NAME} \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/cleanapp-repo/${SERVICE_NAME}:latest \
    --extensions=secrets \
    --set-secrets="MOLTBOOK_API_KEY=moltbook-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest" \
    --set-env-vars="DRY_RUN=false,LOG_LEVEL=INFO" \
    --service-account=${SERVICE_ACCOUNT} \
    --max-retries=0 \
    --region=${REGION}
```

To run it:

```bash
gcloud run jobs execute ${SERVICE_NAME} --region=${REGION}
```

Alternatively, to deploy as a **Service** (always on):

```bash
gcloud run deploy ${SERVICE_NAME} \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/cleanapp-repo/${SERVICE_NAME}:latest \
    --service-account=${SERVICE_ACCOUNT} \
    --set-secrets="MOLTBOOK_API_KEY=moltbook-api-key:latest,GEMINI_API_KEY=gemini-api-key:latest" \
    --set-env-vars="DRY_RUN=false,LOG_LEVEL=INFO" \
    --no-allow-unauthenticated \
    --region=${REGION} \
    --min-instances=1 \
    --memory=512Mi \
    --cpu=1
```

## 6. Verification

Check logs to confirm the agent is running and strictly adhering to policy:

```bash
gcloud logging read "resource.type=cloud_run_job AND resource.labels.job_name=${SERVICE_NAME}" --limit=20
```

## Security Checklist

- [ ] **Dedicated Project/SA**: Agent runs in its own identity silo.
- [ ] **No Inbound Access**: Service is not publicly accessible.
- [ ] **Secrets Managed**: No keys in env vars or code.
- [ ] **Non-Root**: Container runs as `cleanapp` user.
- [ ] **Minimal Scope**: SA only has `secretAccessor` role.
- [ ] **Egress Only**: No VPC connector configured (unless strictly needed).
