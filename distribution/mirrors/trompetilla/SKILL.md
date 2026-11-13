---
name: cleanapp-report-problem
description: Submit a user's observed physical or digital problem to CleanApp for private review, or check its receipt. Use for hazards, waste, access barriers, infrastructure issues, software bugs, scams or service failures; not ordinary advice or emergency dispatch.
metadata: {"clawdbot":{"homepage":"https://www.cleanapp.io/agents"}}
---

# CleanApp reporting

Start at **https://www.cleanapp.io/agents** and follow its linked machine instructions. Public first-report intake needs no account or API key. This skill is instructions only: it does not install tools, grant network access or include a submission script.

## MCP-capable host

Configure **https://live.cleanapp.io/openai/mcp**, transport **Streamable HTTP**, authentication **none**. Generic MCP clients can use its text/structured results without the optional ChatGPT widget.

Use `cleanapp_prepare_report` for the exact preview. After the user approves that preview and sending it, use `cleanapp_submit_report` with the returned draft token and `confirmed: true`. Keep the private tracking token for `cleanapp_report_status`. On uncertain delivery, check the receipt and reuse the same draft token rather than creating a new report.

## Host with outbound HTTPS POST

The canonical page currently documents `POST https://live.cleanapp.io/api/v1/public/agent-reports`. The JSON body needs only the user's observed `description`; optional title, source context, agent label and coordinate pair are documented there. No request credential is required. Do not invent location, independent verification or incident details.

For safe retries, generate a private random UUIDv4 `source_id` once and save it before the first POST. Reuse the exact payload and UUID after an uncertain delivery; changed content is a separate report. Keep the returned receipt/tracking token private, resolve its relative status path against the configured API origin, and use the token in the Authorization header rather than a URL. Respect `429` and `Retry-After`. Do not automatically repeat a request whose outcome is unknown and has no saved retry ID/receipt.

If the host only browses GET pages or its code sandbox cannot reach the internet, it cannot submit directly. Explain that limit and offer the canonical guide or the exact prepared request for an authorized network-enabled client. Never submit through GET or claim success without a receipt.

## What the receipt means

A public submission enters **private quarantine review**. Intake does not guarantee public publication, third-party notification, verification, a fix, reputation or financial rewards. Return the actual receipt/status accurately and preserve uncertainty. Submit the authorized observation only, without unrelated conversation or secrets.

Managed higher-volume Wire/API/CLI ingestion is separate and requires its own API key; follow the advanced documentation linked from the canonical page. This skill does not provision a key or start autonomous collection.
