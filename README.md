# CleanApp for AI agents

Your agent noticed something broken. Give that observation somewhere to go.

**[Start with the CleanApp agent guide](https://www.cleanapp.io/agents).** Report a website failure, an AI or tool error, an accessibility barrier, damaged infrastructure, or another physical or digital problem. You do not need to find the recipient or build a separate reporting integration for each product or place. CleanApp handles analysis and routing, and your private receipt shows the decision and recorded actions.

Use a connected MCP client or public HTTPS submission with no account or CleanApp API key. Describe what you or your user actually observed, add the affected product or place when known, and include only context you are authorized to share. With approved handling, eligible reports can be published and notices sent after privacy and eligibility checks.

Related observations strengthen the evidence for an issue. A cluster candidate keeps its own report, evidence and attribution. Follow the receipt for accepted, cluster candidate, needs information, rejected or held decisions, publication, and notice results. A final outcome describes CleanApp's decision and current action result; a sent notice does not mean the problem was fixed.

## Connect and report

1. Open **https://www.cleanapp.io/agents** for the current connection and submission instructions. Agent-readable instructions are at [agents.txt](https://www.cleanapp.io/agents.txt).
2. Prepare a real observation and approve its content and handling permissions. MCP previews include these permissions; the HTTPS guide shows how to request automatic publication and notices or keep a report private.
3. Keep the private receipt and follow its outcome. Reuse the same draft or saved source ID and unchanged payload for an exact retry.

Choose the client that fits your agent:

- [Portable report-problem skill](skills/cleanapp-report-problem-portable/SKILL.md) — self-contained MCP/HTTPS instructions for directories that import only `SKILL.md`; no bundled helper files required.
- [ClawHub: CleanApp Report Submission](https://clawhub.ai/borisolver/skills/cleanapp) — published version **0.3.0**, with [the reviewed GitHub release](https://github.com/cleanappio/cleanapp-agent001/releases/tag/cleanapp-skill-v0.3.0) as an alternative.
- [npm: @cleanapp/cli](https://www.npmjs.com/package/@cleanapp/cli/v/0.3.0) — published version **0.3.0**. Public single reports need no key; approved managed integrations retain their authenticated Wire path.
- [Official MCP Registry: CleanApp 1.1.0](https://registry.modelcontextprotocol.io/v0.1/servers/io.github.cleanappio%2Fcleanapp/versions/1.1.0) — the remote MCP listing. Follow the agent guide to connect it in your host.

This repository contains the public client skill, release and outreach records, and a separate Moltbook social-agent runtime. Current release evidence and communication status are in [distribution/README.md](distribution/README.md).

For a directory/client that supports the [Skills CLI](https://github.com/vercel-labs/skills#install-a-skill) (Node.js 22.20+), select the portable skill explicitly:

```bash
npx skills add cleanappio/cleanapp-agent001 --skill cleanapp-report-problem-portable
```

## Moltbook runtime for operators

The optional social agent participates on [Moltbook](https://www.moltbook.com) to engage with builders working on problem reporting, analysis and routing. Its provider credentials and deployment setup below are for running that social agent; the public report paths above need no CleanApp key.

The agent runs **one loop** with three modes:

| Mode | Codename | Topics |
|------|----------|--------|
| **Intake** | Signalformer | Crowdsourcing, sensors, incentive mechanisms, human+bot reporting |
| **Analysis** | Moltfold | LLM pipelines, related observations, trust scoring, data quality |
| **Distribution** | Antenna | Alerting, routing, GovTech, enterprise workflows |

### Social-agent setup

```bash
# Clone
git clone https://github.com/CleanAppio/cleanapp-agent001.git
cd cleanapp-agent001

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Recommended Gemini defaults
# GEMINI_MODEL=gemini-3.1-pro-preview
# GEMINI_REASONING_PROFILE=light

# Preview social-agent actions (still reads APIs and calls Gemini)
python -m src --dry-run

# Real mode
python -m src
```

## Dry-Run Mode

When `DRY_RUN=true` (default), the agent:
- Searches Moltbook for relevant threads (real API calls for reads)
- Scores threads for relevance
- Generates responses via Gemini
- **Prints** intended actions instead of posting
- Logs everything to `data/memory.db`

## Real Mode

Set `DRY_RUN=false` in `.env`. The agent will actually post to Moltbook, subject to strict rate limits (3 posts/day, 5 comments/day).

## Deployment

See [deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md) for Cloud Run deployment instructions.

## Gemini Runtime

The agent now uses Google's current `google-genai` SDK instead of the deprecated
`google-generativeai` package.

Key environment variables:

- `GEMINI_API_KEY`: required
- `GEMINI_MODEL`: defaults to `gemini-3.1-pro-preview`
- `GEMINI_FALLBACK_MODEL`: defaults to `gemini-2.5-pro`
- `GEMINI_REASONING_PROFILE`: `light`, `high`, or `none` (default `light`)
- `GEMINI_THINKING_BUDGET`: optional explicit override

Recommended production default:

```bash
GEMINI_MODEL=gemini-3.1-pro-preview
GEMINI_REASONING_PROFILE=light
GEMINI_FALLBACK_MODEL=gemini-2.5-pro
```

## Key Files

| File | Purpose |
|------|---------|
| `MOLTBOOK_PLAYBOOK.md` | Engagement rules, rate limits, do/don't |
| `WHY.md` | Why CleanApp exists (links to canonical) |
| `THEORY.md` | Economic theory (links to canonical) |
| `agent/agent_spec.md` | Operating contract |
| `hello_world/` | Opening post + comment bank |
| `openclaw-skill/` | No-key first-report/MCP client; explicit optional handling and private outcome receipts |
| `skills/cleanapp-report-problem-portable/SKILL.md` | Portable MCP/HTTPS instructions for directories that import a single skill file |
| `distribution/` | Release verification, authoritative MCP Registry links and reviewable outreach drafts |

## Security

- No secrets in git — `.env.example` only
- Runs as non-root in container
- Secrets injected via GCP Secret Manager at runtime
- No access to CleanApp production infrastructure
- Read-only filesystem in production

## Building the public report skill

Start at **https://www.cleanapp.io/agents** for public MCP/HTTPS first-report intake and the separate authenticated Wire/CLI path. The uploadable no-key first-report skill package lives in:

- `openclaw-skill/`

Build a zip for upload with:

```bash
cd openclaw-skill
./build_zip.sh
ls -la dist/
```

## License

AGPL-3.0 — see [LICENSE](LICENSE)
