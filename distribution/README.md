# Agent onboarding release

Canonical entry point: https://www.cleanapp.io/agents.

This repository owns the ClawHub client package and outreach source. Backend intake, frontend discovery and the MCP implementation are separate repositories. No social-agent runtime deployment or posting is part of these source changes.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_onboarding.py' -v
python3 tools/onboarding_acceptance.py
```

The default acceptance run only discovers `/agents` → linked `agents.txt` and asks MCP for its tool inventory. The HTTP/SQLite fixture tests exercise one persisted private report, a clean subprocess without API-key environment, status, exact retry and one invalid-token rejection. That fixture validates the public client contract; backend handler/database integration is checked in the backend repository.

After deployment, the root/operator can run the same client against a **real approved observation** of the onboarding failure, stored in `approved-report.json` outside git:

```bash
python3 tools/onboarding_acceptance.py --submit --input approved-report.json --receipt-file /absolute/private/path/receipt.json
```

This performs exactly one new intake, one exact replay, receipt status and one wrong-token check. It neither registers a managed agent nor uses admin SQL/provider credentials. A passing run prints a token-free summary; the receipt/checkpoint file is 0600 and must remain private. On a failed/unknown delivery, inspect/reuse that file before another run; do not create a fresh source UUID blindly.

## ClawHub release

The existing registry slug is `cleanapp`, owner `borisolver`, latest 0.1.1 at inspection. This source bundle is 0.2.0; required secrets are empty for its public path. Python3 and outbound HTTPS are declared. Advanced authenticated Wire/CLI requirements are documented separately. Build and inspect `openclaw-skill/dist/cleanapp_0.2.0.zip` with `openclaw-skill/build_zip.sh`.

After live acceptance, the root/operator can publish the reviewed directory:

```bash
clawhub publish ./openclaw-skill --slug cleanapp --name 'CleanApp Report Submission' --version 0.2.0 --changelog 'Add no-key public first-report and MCP onboarding, private receipts and safe retries; retain advanced Wire guidance.'
```

Publishing needs an authenticated ClawHub session owned by or authorized for `borisolver`. No standard local ClawHub/Clawdhub auth config or token override was found during preparation; do not copy tokens into commands, this repository or logs. Authentication and actual publishing are root/operator actions. Read the resulting registry metadata/package, then run its installed client as a fresh process to verify the published artifact matches the reviewed source.

## Registry and communication

[Official MCP Registry publishing](registry/README.md) is maintained in the actual MCP implementation repository, using GitHub Actions OIDC. This client/outreach repository keeps links rather than copied registry versions or publishing workflows. [Outreach drafts](outreach.md) await concrete posting approval after technical work. Updating registry/package metadata does not install a connector in Grok, and an indexed listing does not prove an active announcement or a successful report.
