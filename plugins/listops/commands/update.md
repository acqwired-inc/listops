---
description: Update the installed ListOps skills/commands/agent to the latest version from DRA
argument-hint: (none)
---

Re-download and reinstall the ListOps skill pack from the DRA API, using your
already-connected key.

Run: `python ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py update`

This fetches the latest key-gated pack and overwrites the installed files under
your Claude config dir, then prints the installed pack version. Relay that
version. Skills and commands hot-reload; **restart Claude Code** only if the
script indicates the agent or a new command changed.

If it reports no key configured, tell the user to run `/listops:connect <dra_ key>` first.

You rarely need to remember this command: `/listops:status` and
`connect.py check` compare the installed pack version against the server and
nudge when an update is available.
