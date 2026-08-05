---
description: Connect with a pasted API key instead of the browser flow — for when the connector cannot be authorized interactively
argument-hint: <your dra_ API key from the Acqwired dashboard, or blank to check status>
---

The normal path is authorizing the `listops` connector (`/mcp` → `listops` → Authenticate),
after which the pack installs itself on the next start. Use this command when that browser
flow is not available: a headless or CI session, a shared machine, or a server added with a
static auth header.

Argument provided: **$ARGUMENTS**

1. **No argument** → run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py check` and report
   whether a key and pack are installed (masked). If nothing is configured, tell the user to
   authorize the connector, or to re-run this with their `dra_` key. Stop.

2. **Argument starts with `dra_`** → run
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py set --key <the key>`.
   This validates the format, stores the key in `~/.claude/settings.json`, and downloads the
   key-gated pack. An invalid key is rejected server-side (401) and nothing installs.

3. Relay the script output — files installed and pack version — then say **restart Claude Code
   once**: skills hot-reload, but commands and the agent load at startup.

Notes:

- Never echo the full key. The script masks it; do the same.
- If the connector is already authorized, the script says so and stores the key **without**
  adding a second server entry — two entries on one URL would duplicate every tool.
- If it reports a different `DRA_API_KEY` in your shell, surface that: the shell value wins
  over `settings.json`, so it has to be unset or aligned.
- To disconnect: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py clear` (add `--purge` to
  delete the installed files too).

**Claude Desktop:** worth trying if the connector's tools are not responding after you
authorized. Be aware of the mechanism, though — this writes the key and the pack under the
**Claude Code** config directory. If Desktop does not read that location, the script will
report success while no `/listops:*` commands appear; that is not a failure to debug, it
just means the pack landed somewhere Desktop is not looking. The connector's 24 tools are
what Desktop relies on either way.
