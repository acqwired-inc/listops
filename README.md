# This plugin is retired: use the Evergreen connector

ListOps is now **Evergreen**, and it needs no plugin. It is a single MCP connector
that works the same in Claude Code, Claude Desktop, the Claude mobile app, Codex,
Cursor, Copilot and any other MCP client:

```
https://api.acqwired.com/v1/mcp
```

Setup for every client: **https://platform.acqwired.com/evergreen**

## Claude Code

```bash
claude mcp add --transport http evergreen https://api.acqwired.com/v1/mcp
# then, inside Claude Code:  /mcp -> evergreen -> Authenticate
# (a browser opens; paste your Evergreen API key once)
```

If you installed this plugin before, remove it:

```bash
/plugin uninstall listops@acqwired
/plugin marketplace remove acqwired
```

## Claude Desktop, claude.ai and the mobile app

Settings → Connectors → Add custom connector. Name it **Evergreen** and paste the URL
above, then Connect and paste your Evergreen API key when the browser opens.

API keys issued before the rename start with `dra_` and keep working; new keys start
with `evergreen_`. Request a key at https://www.acqwired.com/contact.

This repository is archived and no longer updated.
