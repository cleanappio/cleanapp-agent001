#!/usr/bin/env bash
# CleanApp Report Submission Helper
# Usage: ./submit_report.sh --title "..." --description "..." [options]
#
# Requires: CLEANAPP_API_TOKEN environment variable

set -euo pipefail

# Defaults
API_URL="${CLEANAPP_API_URL:-https://reports.cleanapp.io/api/v3/reports/bulk_ingest}"
SOURCE="openclaw_agent"
CLASSIFICATION="physical"
SEVERITY="0.5"
SCORE="0.7"
LAT=""
LNG=""
TITLE=""
DESCRIPTION=""
URL=""
TAGS=""
BRAND=""
IMAGE_FILE=""
DRY_RUN="${DRY_RUN:-false}"

usage() {
    cat <<EOF
CleanApp Report Submission

Usage: $0 --title "..." --description "..." [options]

Required:
  --title TEXT          Short title (max 500 chars)
  --description TEXT    Detailed description (max 16,000 chars)

Optional:
  --lat FLOAT           Latitude
  --lng FLOAT           Longitude
  --severity FLOAT      Severity 0.0-1.0 (default: 0.5)
  --classification STR  "physical" or "digital" (default: physical)
  --tags STR            Comma-separated tags
  --brand STR           Brand/company name
  --url STR             Source URL
  --score FLOAT         Confidence score 0.0-1.0 (default: 0.7)
  --image FILE          Path to image file (will be base64-encoded)
  --dry-run             Print request without sending
  --api-url URL         Override API endpoint

Environment:
  CLEANAPP_API_TOKEN    Required. Bearer token for authentication.
  CLEANAPP_API_URL      Optional. Override API endpoint.
  DRY_RUN               Set to "true" to print without sending.

Examples:
  $0 --title "Pothole on Oak St" --description "30cm wide, 10cm deep" --lat 37.77 --lng -122.42
  $0 --title "Trash overflow" --description "Dumpster full" --severity 0.8 --brand "Waste Management"
EOF
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --title) TITLE="$2"; shift 2 ;;
        --description) DESCRIPTION="$2"; shift 2 ;;
        --lat) LAT="$2"; shift 2 ;;
        --lng) LNG="$2"; shift 2 ;;
        --severity) SEVERITY="$2"; shift 2 ;;
        --classification) CLASSIFICATION="$2"; shift 2 ;;
        --tags) TAGS="$2"; shift 2 ;;
        --brand) BRAND="$2"; shift 2 ;;
        --url) URL="$2"; shift 2 ;;
        --score) SCORE="$2"; shift 2 ;;
        --image) IMAGE_FILE="$2"; shift 2 ;;
        --dry-run) DRY_RUN="true"; shift ;;
        --api-url) API_URL="$2"; shift 2 ;;
        --help|-h) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

# Validate required fields
if [[ -z "$TITLE" ]]; then
    echo "Error: --title is required"
    usage
fi
if [[ -z "$DESCRIPTION" ]]; then
    echo "Error: --description is required"
    usage
fi
if [[ -z "${CLEANAPP_API_TOKEN:-}" && "$DRY_RUN" != "true" ]]; then
    echo "Error: CLEANAPP_API_TOKEN environment variable is required"
    echo "Set it with: export CLEANAPP_API_TOKEN='your_token_here'"
    exit 1
fi

# Generate external_id
EXTERNAL_ID="openclaw_$(date -u +%Y%m%dT%H%M%S)_$(head -c 8 /dev/urandom | xxd -p)"

# Build tags JSON array
TAGS_JSON="[]"
if [[ -n "$TAGS" ]]; then
    TAGS_JSON=$(echo "$TAGS" | tr ',' '\n' | sed 's/^/"/;s/$/"/' | paste -sd, - | sed 's/^/[/;s/$/]/')
fi

# Handle image base64 encoding
IMAGE_B64=""
if [[ -n "$IMAGE_FILE" && -f "$IMAGE_FILE" ]]; then
    IMAGE_B64=$(base64 < "$IMAGE_FILE" | tr -d '\n')
fi

# Build metadata object
METADATA=$(cat <<METADATA_EOF
{
    "classification": "$CLASSIFICATION",
    "severity_level": $SEVERITY
    $([ -n "$LAT" ] && echo ", \"latitude\": $LAT" || true)
    $([ -n "$LNG" ] && echo ", \"longitude\": $LNG" || true)
    $([ -n "$BRAND" ] && echo ", \"brand_name\": \"$BRAND\"" || true)
}
METADATA_EOF
)

# Build full request
REQUEST=$(cat <<REQUEST_EOF
{
    "source": "$SOURCE",
    "items": [{
        "external_id": "$EXTERNAL_ID",
        "title": $(echo "$TITLE" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))"),
        "content": $(echo "$DESCRIPTION" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))"),
        "url": "$URL",
        "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "score": $SCORE,
        "tags": $TAGS_JSON,
        "metadata": $METADATA
        $([ -n "$IMAGE_B64" ] && echo ", \"image_base64\": \"$IMAGE_B64\"" || true)
    }]
}
REQUEST_EOF
)

if [[ "$DRY_RUN" == "true" ]]; then
    echo "=== DRY RUN ==="
    echo "URL: $API_URL"
    echo "Token: ${CLEANAPP_API_TOKEN:+set (hidden)}"
    echo ""
    echo "$REQUEST" | python3 -m json.tool 2>/dev/null || echo "$REQUEST"
    echo ""
    echo "=== To submit for real, remove --dry-run ==="
    exit 0
fi

# Submit
echo "Submitting report: $TITLE"
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL" \
    -H "Authorization: Bearer $CLEANAPP_API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$REQUEST")

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" == "200" ]]; then
    echo "✅ Report submitted successfully!"
    echo "   External ID: $EXTERNAL_ID"
    echo "   Response: $BODY"
else
    echo "❌ Submission failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
    exit 1
fi
