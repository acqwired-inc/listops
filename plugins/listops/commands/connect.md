---
description: Connect Claude Code to DRA and install the ListOps skills — paste your assigned API key once
argument-hint: <your dra_ API key from the Acqwired dashboard, or blank to check status>
---

Authorize the DRA connection **and install the ListOps skill pack**. The skills,
pipeline commands, and qa-judge agent are NOT bundled in this plugin — they're
downloaded from the DRA API on connect, gated by your (org-validated) key, and
written under your Claude config dir.

Argument provided: **$ARGUMENTS**

Do this:

1. **No argument given** → run `python ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py check`
   and report whether a key and skill pack are installed (masked). If not, tell the
   user: *"Paste your DRA API key from the Acqwired dashboard — run `/listops:connect dra_…`"*. Stop.

2. **Argument looks like a key** (starts with `dra_`) → run
   `python ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py set --key <the key>`.
   This validates the format, stores the key in user-scope `~/.claude/settings.json`,
   then **downloads the key-gated ListOps skill pack** (skills, the build/plan/list/
   enrich/filter/thesis/qa/export/status commands, the qa-judge agent) and
   writes it under the Claude config dir. An invalid key is rejected by the server
   (401) and nothing is installed.

3. Relay the script output (files installed + pack version), then state clearly:
   **restart Claude Code once** — the keyed `dra-research` MCP server and the
   downloaded skills/commands/agent all load at startup.

4. After restart, `/listops:status` confirms the connection + funnel, and the full
   pipeline (`/listops:build`, `/listops:list`, …) is available. `/listops:update`
   re-syncs the skills later.

Notes:
- Never echo the full key — the script masks it; you do the same.
- If the script reports a *shell* `DRA_API_KEY` that differs from the one being set,
  surface it: the shell var wins over settings.json, so it must be unset or aligned.
- To disconnect: `python ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py clear`
  (add `--purge` to also delete the installed skill files).
