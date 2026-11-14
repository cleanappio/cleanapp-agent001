# Agent onboarding and distribution

Canonical entry point: https://www.cleanapp.io/agents.

Use one connection to turn an observed problem into a retained report, an analysis decision and trackable action. The guide explains MCP and no-key HTTPS submission, approved handling, safe retries and private receipt status. Agents do not need to find a recipient first. Related observations are cluster candidates that retain their own evidence and attribution.

This repository owns the ClawHub client package and outreach source. Backend intake, frontend discovery and the MCP implementation are separate repositories. Documentation changes do not deploy the social-agent runtime or publish a post.

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

Verified on **2026-11-14**:

- [`@cleanapp/cli` 0.3.0](https://www.npmjs.com/package/@cleanapp/cli/v/0.3.0) is published on npm. The release passed the reviewed-source publishing workflow; public registry metadata and the tarball were verified.
- [ClawHub `cleanapp` 0.3.0](https://clawhub.ai/borisolver/skills/cleanapp), owned by `borisolver`, is public, installable and Latest. Its public archive matches all eight reviewed source files; only registry metadata was added. Security audit status is Pass.
- [GitHub skill release 0.3.0](https://github.com/cleanappio/cleanapp-agent001/releases/tag/cleanapp-skill-v0.3.0) provides the reviewed `cleanapp_0.3.0.zip` as an alternative distribution path.
- [Official MCP Registry 1.1.0](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.cleanappio%2Fcleanapp/versions/1.1.0) points to the current guide and remote MCP endpoint. Its publication workflow and public record were verified.

These releases support explicit publication and notice permissions and recorded outcomes. Omitted handling remains private/none; older private submissions retain their original permissions. Publication and delivery are separate recorded results, and final does not mean resolved. Required secrets are empty for the public path. The completed releases do not need resubmission.

For 0.3.0, Python3 and outbound HTTPS are declared. Advanced authenticated Wire/CLI requirements are documented separately. Build and inspect `openclaw-skill/dist/cleanapp_0.3.0.zip` with `openclaw-skill/build_zip.sh`.

The reviewed ClawHub upload contains exactly the eight files packaged by `build_zip.sh`. For a directory upload, use the contents of that reviewed archive in a clean staging directory. Uploading the source folder directly can include `build_zip.sh`, generated `dist/` archives and `__pycache__/` files outside the reviewed artifact.

Verify release artifacts by inspecting the published version metadata and files, then checking that the installed client matches the reviewed artifact. Authentication and actual publishing are operator actions; do not copy tokens into commands, this repository or logs.

## Registry and communication

[Official MCP Registry publishing](registry/README.md) is maintained in the actual MCP implementation repository, using GitHub Actions OIDC. This client/outreach repository keeps links rather than copied registry versions or publishing workflows.

The [X announcement published on 2026-11-13](https://x.com/CleanApp/status/2121347177221964087) links the canonical guide. It is an earlier announcement; its existence is separate from any later promotion.

The [new X announcement on 2026-11-14](https://x.com/CleanApp/status/2121663499826782310) introduces the current guide and reporting value. The CleanApp X profile pins the guide announcement.

The [Moltbook announcement](https://www.moltbook.com/post/7717edfa-1535-4f86-9257-39f6ad910337) was created and verified, but its public API readback still marks it as spam, and it was absent from the checked public feed. A moderation review request was sent to Moltbook support on 2026-11-13. The [claimed CleanApp profile](https://www.moltbook.com/u/CleanApp) was updated on 2026-11-14 to describe analysis decisions, related evidence and approved actions; authenticated readback matches, while public-profile propagation remains unconfirmed. No new Moltbook post, reply or repost was created. Do not count the moderated post as confirmed feed distribution or recreate it to bypass moderation.

Directories that import only a skill file should use [the uniquely named portable MCP/HTTPS variant](../skills/cleanapp-report-problem-portable/SKILL.md), `cleanapp-report-problem-portable`. The published OpenClaw 0.3.0 archive remains unchanged. The [earlier agentskill.sh import](https://agentskill.sh/@raw-githubusercontent-com/cleanapp-report-problem) used the packaged skill; replace that directory import with the portable variant so its instructions do not depend on absent helper files. A prepared source file is not proof that a directory has updated its copy.

The [Trompetilla mirror correction PR](https://github.com/Trompetilla/Skills/pull/3) remains open for the upstream maintainer. Its existing public listing still needs the working guide and current instructions; an open correction is not an updated listing.

The owner authorized a new bounded promotion/update effort on 2026-11-14. [Current outreach copy](outreach.md) supports that work; this does not authorize scheduling or an ongoing posting loop. Record actual published URLs and platform results separately. Updating registry/package metadata does not install a connector in Grok, and a listing does not prove an agent connected or submitted a report.
