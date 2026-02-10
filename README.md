# CleanApp Agent001

A Moltbook social agent that engages with other AI agents on topics related to CleanApp's global sensor and routing layer for real-world issues.

## What It Does

CleanApp is building infrastructure that turns diffuse human/agent observations into actionable, routed intelligence. This agent participates on [Moltbook](https://www.moltbook.com) — the social network for AI agents — to find and engage with builders working on related problems.

The agent runs **one loop** with three modes:

| Mode | Codename | Topics |
|------|----------|--------|
| **Intake** | Trashformer | Crowdsourcing, sensors, incentive mechanisms, human+bot reporting |
| **Analysis** | Moltfold | LLM pipelines, dedup, trust scoring, data quality |
| **Distribution** | Antenna | Alerting, routing, GovTech, enterprise workflows |

## Quick Start

```bash
# Clone
git clone https://github.com/CleanAppio/cleanapp-agent001.git
cd cleanapp-agent001

# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your keys

# Dry run (no actual API calls)
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

## Key Files

| File | Purpose |
|------|---------|
| `MOLTBOOK_PLAYBOOK.md` | Engagement rules, rate limits, do/don't |
| `WHY.md` | Why CleanApp exists (links to canonical) |
| `THEORY.md` | Economic theory (links to canonical) |
| `agent/agent_spec.md` | Operating contract |
| `hello_world/` | Opening post + comment bank |

## Security

- No secrets in git — `.env.example` only
- Runs as non-root in container
- Secrets injected via GCP Secret Manager at runtime
- No access to CleanApp production infrastructure
- Read-only filesystem in production

## License

AGPL-3.0 — see [LICENSE](LICENSE)
