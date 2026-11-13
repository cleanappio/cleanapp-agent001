# CleanApp Report Submission 0.2.0

Canonical onboarding: **https://www.cleanapp.io/agents**.

This client-side skill sends one approved observation to CleanApp's public intake and keeps a private receipt. It needs Python3 and outbound HTTPS; no account or CleanApp API key is required. A connected MCP client can instead use the server named on the onboarding page.

Create `approved-report.json` from a real observation, containing at least `description`. Then preview before sending:

```bash
python3 report.py --input approved-report.json --dry-run
python3 report.py --input approved-report.json --submit --receipt-file private-receipt.json
python3 report.py --status --receipt-file private-receipt.json
```

`--dry-run` makes no network calls. `--discover` reads the canonical page and its linked `agents.txt` without submitting. Submission saves a random UUIDv4 before its first request; exact retries use the same file/input with `--retry --submit`. A private receipt file contains a bearer tracking token and must not be posted, committed or placed in shared logs. The client prints no tracking token.

A successful public submission is private/quarantined. Publication, routing, notification, fixes and financial rewards are not promised. See [SKILL.md](SKILL.md) and [API reference](references/API_REFERENCE.md).

## Upgrade from 0.1.x

The default package now targets public **single-report** intake; it no longer requires a Fetcher key or accepts the old bulk `items` envelope. `run.sh`, `ingest.py` and `scripts/submit_report.sh` route to this public client. Existing authenticated bulk integrations and `@cleanapp/cli` remain supported through the separate Wire API; migrate deliberately using the API reference rather than passing a token to this client.

Build an uploadable bundle with `./build_zip.sh`. Publishing is a separate release action; building the archive does not upload or post anything.
