---
name: cleanapp-report-problem
description: Submit an observed physical or digital problem to CleanApp for private review, or check its receipt. Use for a user's report of a hazard, access barrier, waste, broken infrastructure, software bug, scam or service failure. Excludes ordinary advice, emergency dispatch and autonomous bulk collection.
metadata: {"clawdbot":{"homepage":"https://www.cleanapp.io/agents","requires":{"bins":["python3"]}}}
---

# Report a problem to CleanApp

Start at **https://www.cleanapp.io/agents**; its linked `agents.txt` names the current endpoints. The public first-report paths need no account or API key. A listing or skill file supplies instructions; it does not grant network access or install an MCP connector.

Use only the observation the user wants to send. Preserve uncertainty and source context; do not invent a location, incident, independent verification or a promised fix. Include optional coordinates only when supplied or approved. Send the approved report text, not unrelated conversation or credentials.

## Connected MCP client

Connect **https://live.cleanapp.io/openai/mcp** using **Streamable HTTP**, authentication **none**. The `/openai/` path also serves generic MCP clients; the optional interactive widget is for supporting hosts.

1. Call `cleanapp_prepare_report` to produce the exact factual preview.
2. After the user approves that preview and sending it, call `cleanapp_submit_report` with the returned `draft_token` and `confirmed: true`. Reuse that draft token on retry.
3. Return the private receipt. Use `cleanapp_report_status` with its tracking token when asked about status. An unknown delivery is a reason to check the receipt before sending again.

## Client with outbound HTTPS POST

The included Python client discovers the current public endpoint. `description` alone is enough; title, source URL, agent name and coordinates are optional. No CleanApp API token is read or required.

Preview the user's exact report offline:

```bash
python3 report.py --input approved-report.json --dry-run
```

Send only when authorized for that exact content and destination:

```bash
python3 report.py --input approved-report.json --submit --receipt-file private-receipt.json
python3 report.py --status --receipt-file private-receipt.json
```

The client generates a private random UUIDv4 `source_id` before sending and stores its checkpoint/receipt with mode 0600. Keep the receipt file private. If delivery is unknown, reuse the same input and file with `--retry --submit`; do not create another UUID for the same attempt. Changed input must be a separate report.

If the host only browses GET pages, or its execution tool has no outbound network, it cannot submit directly. Explain the missing capability and provide the canonical `/agents` link or the exact prepared request for an authorized network-enabled client. Never turn submission into a GET request or claim a report was sent without a receipt.

## Receipt meaning and advanced ingestion

Public submissions enter a **private quarantine review lane**. A receipt confirms intake status, not public publication, recipient notification, resolution, reputation credit or payment. Respect `429`/`Retry-After`; do not retry aggressively.

For request fields, status, retries and authenticated higher-volume Wire/CLI use, read [the API reference](references/API_REFERENCE.md). The advanced Wire path has separate API-key requirements; this public first-report skill does not provision those keys.
