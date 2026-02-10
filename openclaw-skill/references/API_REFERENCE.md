# CleanApp Bulk Ingest API Reference

## Endpoint

```
POST /api/v3/reports/bulk_ingest
```

**Base URL**: `https://reports.cleanapp.io`

## Authentication

Bearer token in the `Authorization` header:

```
Authorization: Bearer <your_token>
```

Tokens are provisioned per-fetcher and validated against the `fetchers` table (SHA-256 hashed).

## Request Schema

```json
{
  "source": "openclaw_agent",
  "items": [
    {
      "external_id": "string (required, unique per source)",
      "title": "string (required, max 500 chars)",
      "content": "string (required, max 16,000 chars)",
      "url": "string (optional, max 500 chars)",
      "created_at": "ISO 8601 timestamp (optional)",
      "updated_at": "ISO 8601 timestamp (optional)",
      "score": "float 0.0-1.0 (optional, confidence score)",
      "tags": ["string array (optional)"],
      "skip_ai": "boolean (optional, skip AI analysis)",
      "image_base64": "string (optional, base64-encoded image)",
      "metadata": {
        "latitude": "float (optional)",
        "longitude": "float (optional)",
        "classification": "\"physical\" or \"digital\" (optional, default: digital)",
        "severity_level": "float 0.0-1.0 (optional)",
        "litter_probability": "float 0.0-1.0 (optional)",
        "hazard_probability": "float 0.0-1.0 (optional)",
        "digital_bug_probability": "float 0.0-1.0 (optional)",
        "brand_name": "string (optional)",
        "language": "ISO 639-1 code (optional, default: en)",
        "summary": "string (optional, custom summary)",
        "inferred_contact_emails": ["string array (optional)"],
        "needs_ai_review": "boolean (optional)",
        "skip_side_effects": "boolean (optional, skip RabbitMQ)",
        "bulk_mode": "boolean (optional, skip side effects + AI review)"
      }
    }
  ]
}
```

## Limits

- Max **1000 items** per request
- Title truncated to 500 runes
- Content truncated to 16,000 runes
- URL truncated to 500 runes
- Duplicate `external_id` + `source` combinations are silently skipped

## Response Schema

```json
{
  "inserted": 5,
  "updated": 0,
  "skipped": 2,
  "errors": [
    { "i": 3, "reason": "missing external_id" }
  ]
}
```

## Error Codes

| HTTP | Meaning |
|------|---------|
| 200 | Success (check `inserted` / `skipped` counts) |
| 400 | Invalid JSON, missing `source`/`items`, or >1000 items |
| 401 | Missing or invalid Bearer token |
| 500 | Database or internal error |

## What Happens After Ingestion

1. Report inserted into `reports` table with auto-incremented `seq`
2. Analysis record created in `report_analysis` table
3. External ingest index updated for deduplication
4. Report details (company, product, URL) stored
5. If not in fast-path mode: report published to RabbitMQ for real-time rendering
6. AI analysis pipeline picks up reports for enrichment (brand extraction, severity scoring, clustering)
7. Distribution pipeline routes alerts to responsible parties
