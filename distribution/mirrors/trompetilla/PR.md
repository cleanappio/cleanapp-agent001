# Correct CleanApp skill endpoint, capability requirements and receipt claims

The mirrored CleanApp skill points to `reports.cleanapp.io`, which currently fails DNS resolution, and references a helper script that is absent from this mirror (the directory contains only SKILL.md and _meta.json). It also describes automatic public publication/routing as a submission outcome.

Replace the instructions with the current canonical `/agents` guide, working no-auth MCP/public first-report paths, explicit host tool/network requirements, safe UUID/draft-token retries, and private quarantine receipt semantics. Keep managed authenticated Wire/CLI as a separate advanced path. Do not modify the registry-generated _meta.json or claim a listing installs an MCP connector.

Validation: upstream public onboarding/MCP discovery, HTTP/SQLite fresh-client receipt/replay/isolation fixture in the maintained CleanApp client repository, and skill frontmatter validation. This mirror patch contains no credential and makes no submission.

Prepared against Trompetilla/Skills main a4277979986e03177b86838f836c5d69c11e8052; original SKILL.md blob e5f6a2961fbd29edcf4dd555f65b4c6867c9fefe. Current authenticated user has READ permission, so an upstream pull request/fork is needed; no external PR/comment has been posted during preparation.
