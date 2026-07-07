# ListOps — Acqwired plugin for Claude Code & Claude Desktop

Investment-grade company list building. Turn a one-line ask —
*"commercial landscaping companies in Texas, owner-operated, >$5M, no PE"* — into
a screened, enriched, thesis-ranked list, powered by the
**Acqwired Research API** (DRA — your API key starts with `dra_`).

## Install — Claude Desktop

1. **Customize → Plugins → Add marketplace** — search for `acqwired-inc/listops-mcp-server`, browse to **Personal**, click **+**.
2. On the plugin page, find **dra-research** under **Connectors** and click it.
3. A browser window opens at **platform.acqwired.com/connect** — paste your `dra_…` API key and click **Authorize**.
4. Claude Desktop stores the token. Run `/listops:status` to confirm.

> **Seeing "Contact an organization owner to install connectors"?**  
> Your account is on a managed org plan. Ask your org admin to enable connector
> installation in Settings → Organization → Permissions, or use a personal
> Claude Desktop account.

## Install — Claude Code (CLI)

```bash
# 1. add this marketplace
/plugin marketplace add acqwired-inc/listops-mcp-server
# 2. install the plugin
/plugin install listops@acqwired
# 3. connect with your Acqwired API key (starts with dra_)
/listops:connect dra_your_key_here
# 4. restart Claude Code, then:
/listops:status
```

`/listops:build <your thesis>` runs the full pipeline; `/listops:update`
keeps the skills current.

## How it works — thin bootstrap, key-gated skills

This repository is intentionally **thin**. It contains only:

- `.mcp.json` — wires the `dra-research` MCP server (`https://api.acqwired.com/v1/mcp`)
- `/listops:connect` and `/listops:update` commands + `connect.py`

The actual skills, pipeline commands, and the QA agent are **not** in this repo.
On `/listops:connect`, the script validates your key, then **downloads the ListOps
skill pack from the DRA API** — gated server-side by your (org-validated) key — and
installs it under `~/.claude/`. The intelligence stays server-side; an invalid key
gets nothing.

```
install plugin → /listops:connect <key> → pack downloads (key-gated) → restart → full pipeline
```

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

- Claude Code
- An Acqwired API key (`dra_…`) from the [Acqwired dashboard](https://acqwired.com)
- Python 3.8+ on PATH (the bootstrap script is stdlib-only)

## Support

Questions or a key request: contact Acqwired. Issues with the plugin bootstrap can
be filed on this repo.
