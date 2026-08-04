---
description: Force a ListOps skill-pack refresh now, without restarting — for when a new pack ships mid-session
argument-hint: (none)
---

**You rarely need this.** The pack installs and self-updates from a session-start hook,
which compares the installed version against the server on every start and re-downloads
only on a change. This command exists for the one case the hook cannot cover: a new pack
shipping *during* a session, when waiting for the next start is not acceptable.

Run: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/connect.py update`

It re-downloads unconditionally — no version comparison — using the connector's OAuth
credential, or `DRA_API_KEY` if there is no connector.

Relay the script's output verbatim: whether it was already current, the version it moved
to, and the file count. Then note that **skills hot-reload, but commands and the agent
load at startup** — so if the update changed those, a restart is still needed for them to
appear. Do not claim new commands are available without one.

If it reports no credential, the connector was never authorized and no key is set:
tell the user to authorize it (`/mcp` → `listops` → Authenticate), or export
`DRA_API_KEY` for a headless setup.
