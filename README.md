# ListOps — Acqwired plugin for Claude Code & Claude Desktop

Investment-grade company list building. Turn a one-line ask —
*"commercial landscaping companies in Texas, owner-operated, >$5M, no PE"* — into
a screened, enriched, thesis-ranked list, powered by the
**Acqwired Research API** (DRA — your API key starts with `dra_`).

## Install — Claude Desktop

1. **Customize → Plugins → Add marketplace** — search for `acqwired-inc/listops`, browse to **Personal**, click **+**.
2. On the plugin page, find **evergreen** under **Connectors** and click it.
3. A browser window opens at **platform.acqwired.com/connect** — paste your `dra_…` API key and click **Authorize**.
4. Claude Desktop stores the token. Run `/listops:status` to confirm.

> **Seeing "Contact an organization owner to install connectors"?**  
> Your account is on a managed org plan. Ask your org admin to enable connector
> installation in Settings → Organization → Permissions, or use a personal
> Claude Desktop account.

## Install — Claude Code (CLI)

```bash
# 1. add this marketplace
/plugin marketplace add acqwired-inc/listops
# 2. install the plugin
/plugin install listops@acqwired
# 3. authorize the connector:  /mcp  ->  evergreen  ->  Authenticate
#    (a browser opens; paste your dra_ key once)
# 4. restart Claude Code, then:
/listops:status
```

**Authorizing the connector is the only setup step.** There is no second key to
paste: the DRA authorization server is bring-your-own-key, so the token it issues
*is* your `dra_` key. On the next session start the plugin reads that credential,
installs the skill pack itself, and keeps it current from then on.

`/listops:build <your thesis>` runs the full pipeline.

<details>
<summary>Manual setup — CI, custom <code>CLAUDE_CONFIG_DIR</code>, or header auth</summary>

`/listops:connect dra_your_key_here` does the same job from a pasted key, for cases
where there is no OAuth credential to read: CI, a shared machine, or a server added
with `claude mcp add -H "Authorization: ..."`. `/listops:update` re-syncs on demand.
</details>

## How it works — thin bootstrap, key-gated skills

This repository is intentionally **thin**. It contains only:

- `.mcp.json` — wires the `evergreen` MCP server (`https://api.acqwired.com/v1/mcp`)
- `hooks/hooks.json` — a `SessionStart` hook that installs and refreshes the pack
- `/listops:connect` and `/listops:update` commands + `connect.py`

The actual skills, pipeline commands, and the QA agent are **not** in this repo.
The hook **downloads the ListOps skill pack from the DRA API** — gated server-side by
your (org-validated) key — and installs it under `~/.claude/`. The intelligence stays
server-side; an invalid key gets nothing.

```
install plugin → authorize connector → restart → pack installs itself → full pipeline
```

The hook never asks for anything and never blocks a session: if the connector is not
authorized yet, or the credential cannot be read, it prints the manual instruction and
exits cleanly. It downloads only when the pack is missing or the server has a newer
version, so ordinary session starts cost one small request.

On **Claude Desktop** there is no `~/.claude` to install into, so the pipeline commands
are served over MCP as prompts instead — same commands, no download.

## What you get after connect

| Command | Stage |
|---|---|
| `/listops:build <thesis>` | Full pipeline: plan → list → screen → enrich (piloted + reviewed) → filter → thesis → QA → verified export |
| `/listops:list` | Multi-source discovery (Google Maps + Exa) → dedupe → intake screen |
| `/listops:enrich` · `/listops:filter` | Tiered enrich→filter waterfalls with a required pilot review gate |
| `/listops:thesis` | `completeCompanyProfile` + thesis fit scoring |
| `/listops:qa` | Independent QA (ownership re-verification, coverage probes) |
| `/listops:export` | Gap-fill + deterministic basics verification + final deliverable |
| `/listops:conflict-check` | Hand finalists to your internal conflict process |
| `/listops:contacts` | Opt-in leadership contacts, cleared companies only |
| `/listops:status` | Session funnel, gates, credits + update nudge |

Plain language works too — *"find founder-owned HVAC companies near Tampa"* — the
`list-building` skill triggers on intent.

## Requirements

- Claude Code (CLI) or Claude Desktop
- An Acqwired API key (`dra_…`) from the [Acqwired dashboard](https://acqwired.com)
- Python 3.8+ on PATH for the Claude Code path (the bootstrap script is stdlib-only)

## Support

Questions or a key request: contact Acqwired. Issues with the plugin bootstrap can
be filed on this repo.
