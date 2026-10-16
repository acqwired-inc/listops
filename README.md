# ListOps — Acqwired connector for Claude

Company list building on the **Acqwired Research API**. Ask in plain language —
*"commercial landscaping companies in the Sun Belt, owner-operated, no PE"* — and
ListOps asks the few questions that decide the list (size, ownership, end market,
geography), searches the Evergreen company corpus first, uses paid list-building
sources (Google Maps, Exa, Ocean.io) only with your approval, and hands back a
screened, QA'd list as a download link. Every run is kept as a session on the server.

ListOps is **one MCP connector**: `https://api.acqwired.com/v1/mcp`. This plugin just
adds it to Claude Code. It works the same in Claude Desktop, the Claude mobile app,
Codex, Cursor, Copilot and any other MCP client — add the URL there directly.

## Install — Claude Code

```bash
/plugin marketplace add acqwired-inc/listops
/plugin install listops@acqwired
# then:  /mcp  ->  listops  ->  Authenticate   (a browser opens; paste your dra_ key once)
```

Or skip the plugin: `claude mcp add --transport http listops https://api.acqwired.com/v1/mcp`.

No browser (CI, a shared machine)? Add the server with a header instead:
`claude mcp add --transport http listops https://api.acqwired.com/v1/mcp --header "Authorization: Bearer dra_..."`.

## Install — Claude Desktop / mobile

Settings → Connectors → **Add custom connector** → name `Listops`, URL
`https://api.acqwired.com/v1/mcp` → **Connect**, paste your `dra_…` key, **Authorize**.

> **"Contact an organization owner to install connectors"?** Your account is on a managed
> org plan — ask the org admin to allow connector installation, or use a personal account.

## Requirements

- An Acqwired API key (`dra_…`) — contact Acqwired to request one
