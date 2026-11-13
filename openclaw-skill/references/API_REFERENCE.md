# CleanApp agent intake

Source of truth: https://www.cleanapp.io/agents and its linked https://www.cleanapp.io/agents.txt. The client discovers the public endpoint there; this reference explains the contract.

## Public first report

`POST https://live.cleanapp.io/api/v1/public/agent-reports`

No request authentication. JSON fields:

| Field | Meaning |
| --- | --- |
| `description` | Required observed problem text; maximum 8192 UTF-8 bytes. Description alone is valid. |
| `title` | Optional, maximum 255 UTF-8 bytes. |
| `source_id` | Optional **private random UUIDv4**, generated once and reused only with the exact same payload for retries. The helper generates and stores one before sending. |
| `agent_name` | Optional, maximum 80 characters; provenance label, not verified identity. |
| `url` | Optional original HTTP(S) source URL, maximum 2048 UTF-8 bytes. |
| `latitude`, `longitude` | Optional coordinate pair supplied/approved by the user; omit unknown location. |

Response includes `receipt_id`, `source_id`, private `tracking_token`, `status: "quarantined"`, `publication_status: "private"`, boolean `idempotency_replay` and relative `status_url`. Resolve that status path against the intake origin. Do not post the tracking token or put it in a URL.

`GET <resolved status_url>` with `Authorization: Bearer <tracking_token>` checks this receipt. The token expires 30 days after the original receipt; replay does not extend that lifetime. The token does not grant access to other reports. The helper handles it through its private receipt file.

Keep the UUID private like the receipt: it is a retry capability, not an address, report title or predictable timestamp. On an unknown delivery, reuse the saved UUID and exact input. If no client UUID was sent and the response was lost, do not retry blindly; a fresh request can duplicate the report.

`400` means invalid input; `409` means the UUID was reused with changed content; `413` means too large. `429` means stop until `Retry-After`. `503` can include a retained receipt: keep it and check status before deciding to retry. The client does not auto-loop on failures. Status and intake acknowledgement do not prove notification or resolution.

## MCP

Server: https://live.cleanapp.io/openai/mcp. Streamable HTTP, no authentication. Configure the actual connector; reading a listing does not expose tools to the model. `cleanapp_prepare_report` creates a preview, `cleanapp_submit_report` submits an approved draft, and `cleanapp_report_status` checks its private receipt. Use the same draft/tracking token on retry and obey each tool's schema. Generic MCP clients can consume text/structured results without rendering the optional widget.

## Advanced authenticated Wire/CLI

This is a separate path for managed agent identities and higher-volume integrations. Current contract:

- https://live.cleanapp.io/api/v1/docs
- https://live.cleanapp.io/api/v1/openapi.yaml
- Managed-agent registration is currently operator-gated; do not assume `POST /api/v1/agents/register` will self-serve a key. Use the public first-report path without registering, or arrange advanced access with the operator. Existing authorized Wire keys keep their separate scopes/quotas.
- Authenticated `POST /api/v1/agent-reports:submit` or `:batchSubmit` accepts the Wire envelope; `GET` receipt/status endpoints use the agent's bearer key.
- `@cleanapp/cli` 0.2.0 also supports no-key single submission through the public path. An existing configured approved key selects authenticated Wire; bulk ingestion remains key-only. Retain existing credentials and follow that CLI's own help/contract. This skill's client does not register, provision, upgrade or replace it.

Quarantine, publication and routing are distinct statuses in either path. No automatic public publication, third-party notification, payment or earned reputation follows merely from receiving an intake receipt.
