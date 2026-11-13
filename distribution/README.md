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

## Package release status

As of 2026-11-13, [`@cleanapp/cli` 0.2.0](https://www.npmjs.com/package/@cleanapp/cli/v/0.2.0) is published on npm. The ClawHub skill `cleanapp`, owned by `borisolver`, was submitted once as 0.2.0 and is now public and installable, with 0.2.0 verified as **Latest** in the listing's Versions tab. **Do not resubmit this completed release.**

This source bundle is 0.2.0; required secrets are empty for its public path. Python3 and outbound HTTPS are declared. Advanced authenticated Wire/CLI requirements are documented separately. Build and inspect `openclaw-skill/dist/cleanapp_0.2.0.zip` with `openclaw-skill/build_zip.sh`.

The reviewed ClawHub upload contains exactly the eight files packaged by `build_zip.sh`. For a directory upload, use the contents of that reviewed archive in a clean staging directory. Uploading the source folder directly can include `build_zip.sh`, generated `dist/` archives and `__pycache__/` files outside the reviewed artifact.

Verify release artifacts by inspecting the published version metadata and files, then checking that the installed client matches the reviewed artifact. Authentication and actual publishing are operator actions; do not copy tokens into commands, this repository or logs.

## Registry and communication

[Official MCP Registry publishing](registry/README.md) is maintained in the actual MCP implementation repository, using GitHub Actions OIDC. This client/outreach repository keeps links rather than copied registry versions or publishing workflows.

On 2026-11-13, the owner approved one announcement each on X and Moltbook. The [X announcement](https://x.com/CleanApp/status/2121347177221964087) is published. The [Moltbook announcement](https://www.moltbook.com/post/7717edfa-1535-4f86-9257-39f6ad910337) was created and verified, but its readback marks it as spam and it was absent from the checked public feed. [Outreach drafts](outreach.md) remain reference copy; further posts, messages or ongoing campaigns require separate approval. Updating registry/package metadata does not install a connector in Grok, and an indexed listing does not prove an active announcement or a successful report.
