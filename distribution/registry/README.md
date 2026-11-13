# Authoritative MCP Registry publication

The MCP server's registry metadata and manual GitHub Actions OIDC publication belong to the actual implementation repository, **[cleanappio/cleanapp-openai](https://github.com/cleanappio/cleanapp-openai)**:

- [Authoritative server.json](https://github.com/cleanappio/cleanapp-openai/blob/main/server.json)
- [Manual registry publishing workflow](https://github.com/cleanappio/cleanapp-openai/blob/main/.github/workflows/publish-mcp-registry.yml)

That implementation repository is currently private; these links require authorized repository access. This public agent/client repository is not the MCP server source and does not maintain a copied registry version or publishing workflow.

Public registry namespace: **`io.github.cleanappio/cleanapp`**. [Look up the namespace in the official registry](https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.cleanappio%2Fcleanapp). A registry record describes distribution; it does not prove that a particular AI host has connected the server or submitted a report.

The public onboarding source is **https://www.cleanapp.io/agents**. Use its current endpoint and live MCP tool inventory for client setup; use the implementation repository's reviewed metadata/workflow for release instructions.
