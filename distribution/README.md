# Agent onboarding and distribution

Canonical entry point: https://www.cleanapp.io/agents.

Use one connection to turn an observed problem into a retained report, an analysis decision and trackable action. The guide explains MCP and no-key HTTPS submission, approved handling, safe retries and private receipt status. Agents do not need to find a recipient first. Related observations are cluster candidates that retain their own evidence and attribution.

This repository owns the ClawHub client package and outreach source. Backend intake, frontend discovery and the MCP implementation are separate repositories. Documentation changes do not deploy the social-agent runtime or publish a post.

## Verification

```bash
python3 -m unittest discover -s tests -p 'test_onboarding.py' -v
python3 -B tools/onboarding_acceptance.py --discovery-probe --timeout 10
```

The read-only probe checks the homepage link to `/agents`, follows the guide to the linked `agents.txt`, negotiates a fresh MCP session and checks its tool inventory. The registry check verifies that the exact lookup and a brand search both find the active CleanApp listing and agree on the guide, MCP endpoint and live MCP version. The probe uses no provider keys, models, tool invocations or report submissions. A successful run establishes availability from this client at the time checked. Installs, host-specific tool selection, intake and repeat use require separate evidence.

[Agent discovery probe](../.github/workflows/agent-discovery.yml) runs at minute 17 every six hours UTC and supports manual runs. It uses one GitHub-hosted runner with a three-minute timeout and read-only repository access. A blocked request or inconsistent result fails the job with the affected surface named. See the [workflow runs](https://github.com/cleanappio/cleanapp-agent001/actions/workflows/agent-discovery.yml) for execution evidence and timing.

The HTTP/SQLite fixture tests exercise one persisted private report, a clean subprocess without API-key environment, status, exact retry and one invalid-token rejection. That fixture validates the public client contract. Backend handler and database integration are checked in the backend repository.

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

### Public distribution status — 2026-11-14

| Surface | Verified state |
| --- | --- |
| [X](https://x.com/CleanApp/status/2121663499826782310) | New guide announcement published and pinned on the CleanApp profile. The [November 13 announcement](https://x.com/CleanApp/status/2121347177221964087) is historical. |
| [Moltbook profile](https://www.moltbook.com/u/CleanApp) | Updated description is visible publicly; public readback matched at 18:31 UTC. The [older post](https://www.moltbook.com/post/7717edfa-1535-4f86-9257-39f6ad910337) remains verified but marked as spam. A support review was requested on November 13; no new post, reply or repost was created. |
| [agentskill.sh portable skill](https://agentskill.sh/@raw-githubusercontent-com/cleanapp-report-problem-portable) | Public standalone instructions and source guide verified. This is the recommended single-file directory variant. |
| [MCPServers.org](https://mcpservers.org) | Free submission confirmed; confirmation indicated review within two weeks. Not a live listing yet. |
| [MCPMarket AgentSkill](https://mcpmarket.com) | Free submission queue confirmed, with an estimated 4–6 weeks. Not a live listing yet. The paid remote-MCP listing option was declined. |
| [AIAnytime PR 546](https://github.com/AIAnytime/Awesome-MCP-Servers/pull/546) | Open submission; awaiting the upstream maintainer. |
| [TensorBlock PR 6006](https://github.com/TensorBlock/awesome-mcp-servers/pull/6006) | Open submission; awaiting the upstream maintainer. |
| [Trompetilla PR 3](https://github.com/Trompetilla/Skills/pull/3) | Open correction, refreshed with current instructions at commit `676da99`. Registry-generated `_meta.json` was not changed. |
| [Glama](https://glama.ai/mcp/servers) | Existing listing is healthy at 1.1.0 with five tools and the current description. A guide/category correction was requested through Report Issue; no resulting public change is claimed. |
| [OpenAI public listing](https://chatgpt.com/plugins/plugin_asdk_app_6ac34b4d108081918637006965cec037) | Portal confirms package 1.0.3 is Published and listed publicly. The hosted web entry now offers the agent guide and real install link. Prepared 1.1.0 store metadata has not been uploaded or published. |

Directories that import only a skill file should use [the portable MCP/HTTPS variant](../skills/cleanapp-report-problem-portable/SKILL.md), `cleanapp-report-problem-portable`. The [earlier agentskill.sh packaged import](https://agentskill.sh/@raw-githubusercontent-com/cleanapp-report-problem) includes optional helper references and is not the recommended standalone entry. The published OpenClaw 0.3.0 archive remains unchanged; ClawHub 0.3.0 and the official MCP Registry 1.1.0 already point to the correct guide.

The owner authorized this bounded promotion/update effort. [Outreach copy](outreach.md) supports it; no recurring campaign or runtime was started. Submitted, queued and open-PR entries above are not live listings. A listing does not install a connector in an agent host or prove a report was submitted. The moderated Moltbook post is not confirmed feed distribution and has not been recreated to bypass moderation.
