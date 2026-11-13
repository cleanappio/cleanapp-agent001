# Official MCP Registry release staging

These files belong in the **actual MCP implementation repository**, `cleanappio/cleanapp-openai`, after review:

- `server.json` → repository root.
- `publish-mcp-registry.yml` → `.github/workflows/publish-mcp-registry.yml`.

That implementation is currently private. The manifest intentionally omits `repository`; agent001 is the outreach/client repository and must not be misrepresented as the server source. A remote-only registry entry does not require an npm package or public source repository. Version 1.0.3 matches the inspected MCP source package; the operator must confirm the intended deployed version before publishing.

The workflow runs **only by manual dispatch**, only on main in that MCP repository, and requires the exact reviewed SHA/version. It validates metadata and reads live discovery/tool definitions before authenticating. The official publisher is pinned to v1.8.9, its Linux amd64 release SHA256, and a Sigstore release identity. It uses GitHub Actions OIDC; it does not transfer a local GitHub PAT, generate a domain key, modify DNS, or publish an npm package. Its `id-token: write` is restricted to the manually dispatched publish job.

Root/operator sequence after merge, live acceptance and review:

1. Confirm registry namespace `io.github.cleanappio/cleanapp`, source version and remote URL.
2. Dispatch the workflow from the MCP repository's main branch with its full reviewed SHA and manifest version.
3. Read the published record and independently run MCP discovery again. A registry record is distribution metadata, not proof that another host has connected it.

Do not enable push/tag autopublishing for this first release. No workflow has been installed or dispatched by creating these staging files.

Official references: [remote-only publishing](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/quickstart.mdx), [GitHub Actions OIDC](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx), [namespace authentication](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/authentication.mdx), [pinned publisher release](https://github.com/modelcontextprotocol/registry/releases/tag/v1.8.9).
