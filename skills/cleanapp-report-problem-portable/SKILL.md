---
name: cleanapp-report-problem-portable
description: Prepare and submit an observed physical or digital problem to CleanApp, then track its decision and action receipts through MCP or HTTPS. Use for software or AI errors, scams, service failures, accessibility barriers, hazards or damaged infrastructure; not ordinary cleaning advice or emergency dispatch.
metadata: {"homepage":"https://www.cleanapp.io/agents"}
---

# Report a problem with CleanApp

Start with [the agent guide](https://www.cleanapp.io/agents) and [machine instructions](https://www.cleanapp.io/agents.txt) for current contracts. This portable skill needs no bundled scripts. CleanApp handles analysis and routing; the reporter does not need to find the recipient.

Preserve what the user or agent actually observed, the source and uncertainty. Add the affected product, URL or place when known. Concrete AI/tool failures are reportable; another assistant's claim that a bug was verified or fixed is not verification. Never invent facts, coordinates, affected people, successful tests or outcomes. Include only information authorized for sharing; omit credentials, private contact details and unrelated confidential context. Do not create synthetic reports to test connectivity. CleanApp is not emergency dispatch.

## Prefer a connected MCP client

Use the CleanApp tools and schemas already exposed by the host. When configuring a new remote MCP client, connect using Streamable HTTP to **https://live.cleanapp.io/openai/mcp**, without authentication; clients implementing the transport initialize and request `tools/list`. An already connected agent does not need separate protocol tools. If no MCP connection exists, use the HTTPS alternative below. GET-only browsing cannot submit; explain the missing capability rather than claim success.

1. Call `cleanapp_prepare_report` with the observation and relevant product/place context. Preparing returns a preview, not a submitted report.
2. Show the exact preview and its handling permissions. New previews normally request `{"publication":"automatic","notices":"automatic"}`. Offer `{"publication":"private","notices":"none"}` when private handling is requested. Obtain approval for the exact content, permissions and transmission before submitting.
3. Call `cleanapp_submit_report` with the unchanged `draft_token` and `confirmed:true` only after that approval. Keep the same token on an exact retry; editing requires a new approved preview. Never upgrade an older private draft's permissions.
4. Retain the private receipt and `tracking_token`. Use `cleanapp_report_status` to follow its outcome. If submission times out, check status before retrying.

## Plain HTTPS alternative

Send **POST https://live.cleanapp.io/api/v1/public/agent-reports** with `Content-Type: application/json`. Submission requires no Authorization header, registration or API key.

The client must be able to generate a UUIDv4, privately retain the payload and receipt, and read the POST response. Following status also requires HTTPS GET with an Authorization header. Explain any missing capability; a POST-only tool does not establish that status can be checked.

The required field is `description`: a nonempty observation, at most 8192 UTF-8 bytes. Optional fields include `title`, `agent_name`, `url`, paired `latitude`/`longitude`, `source_id` and `handling`; consult the guide/OpenAPI for limits. Do not send a guessed URL or location. Approve the exact payload and handling before transmission.

Generate and privately save a random UUIDv4 `source_id` once before the first POST. Never use a shared example ID or public URL. Include explicitly approved `handling` to authorize eligible publication/notices; omission stays private/none. Permission never bypasses analysis or privacy checks.

Keep the returned `receipt_id`, `source_id`, `tracking_token` and `status_url` private. Resolve `status_url` against **https://live.cleanapp.io** and require that exact origin. GET that URL with `Authorization: Bearer <tracking_token>`. The token grants receipt access, not general API access; keep it out of URLs, public output and shared logs.

After an uncertain POST, check the receipt if available, otherwise retry the unchanged payload with the same saved UUID. Do not blindly resubmit after losing a server-generated ID. For 409, compare the privately saved original payload; for 429, honor `Retry-After`; for 503, retain any receipt and check status before retrying.

## Return the recorded outcome

Follow `outcome.processing`, `decision`, `publication`, `delivery`, `next_action` and `final`. While `final` is false, check the existing receipt without creating another report. Decisions include accepted, cluster candidate, needs information, rejected and held. A cluster candidate adds related evidence while retaining its own report and attribution; do not dismiss it as a duplicate. An exact request replay is a separate idempotency fact.

Report missing information or holds faithfully. Corrections require a newly approved observation with a new source ID; retain the original receipt. Distinguish pending, sent, held, failed and uncertain delivery. Final describes CleanApp's decision and current action result, not resolution, recipient readership, verified responsibility or payment.
