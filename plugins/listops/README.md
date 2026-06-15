# ListOps

Investment-grade company list building for Claude Code, powered by the Acqwired
DRA platform. Turn a one-line request — *"commercial landscape maintenance
companies within 90 miles of these addresses, owner-operated, >$5M, no PE"* —
into a screened, enriched, thesis-ranked export.

**Discovery runs through the DRA `submit_company_list` API, never through Claude
web search.** Live sources in v1 are **Google Maps** (POI) and **Exa** (neural);
Yelp, Foursquare, and Tavily are accepted but not yet implemented (they return
zero hits with a `not_implemented` per-source error — don't plan to depend on
them). Claude skills supply the intelligence: which sources, keywords, locations,
radii, schemas, filters, and thesis.

## Pipeline

```
PLAN → LIST → INTAKE SCREEN → [no requirements? → export offer]
     → (ENRICH tier → FILTER)×N → THESIS → QA → GAP-FILL → EXPORT
```

| Stage | What happens |
|---|---|
| **Plan** | MECE source payload (keywords × locations × radius ≤ 90mi), schema pack with explicit pass/fail rules, thesis text, reserved QA probes, credit budget |
| **List** | `submit_company_list` → poll → `companies.jsonl` with per-source provenance |
| **Intake screen** | Free local screening: dedupe, PE/franchise blocklist (~60 curated platforms shipped), category sanity, website-gap flags |
| **Enrich + Filter (tiered)** | Schemas ordered by kill-rate per credit; tier 1 → filter → tier 2 on survivors → … Each tier credit-gated; confidence <50 = data gap, not rejection |
| **Thesis** | `completeCompanyProfile` + thesis text on survivors → rank by `thesis_fit_score` |
| **QA** | Independent judge: spot-checks, mandatory ownership re-verification, coverage probes via the list API |
| **Gap-fill + Export** | `reconstruct`-first field completion → `final.csv` with provenance + confidence |

Every run is tracked in **`lists/<slug>/session-tracking-<id>.json`** (atomic
writes) — any session or command resumes exactly where the last one stopped.

## Setup

This plugin is a **thin bootstrap**. Installing it gives you two commands —
`/listops:connect` and `/listops:update`. The skills, pipeline commands, and the
QA agent are **not shipped in the marketplace**; they're **downloaded from the DRA
API on connect**, gated by a valid (org-validated) key, and written under
`~/.claude/`. The proprietary logic never sits in a public repo.

1. Install the plugin (marketplace README one level up). The bundled `.mcp.json`
   wires the `dra-research` MCP server.
2. **Connect.** Get your assigned key from the Acqwired dashboard (Settings → API
   key), then run `/listops:connect dra_...`. This validates the key, stores it in
   user-scope `~/.claude/settings.json`, and **downloads + installs the ListOps
   skill pack**. An invalid key is rejected server-side (401) and nothing installs.
3. **Restart Claude Code once** — the keyed MCP server and the downloaded
   skills/commands/agent all load at startup. Then `/listops:status` confirms.
4. `/listops:update` re-syncs the skills to the latest version anytime.

Requires Python 3.8+ on PATH (the bootstrap script is stdlib-only).
*(CI / power users: export `DRA_API_KEY=dra_...` in the shell — it takes
precedence over settings.json — then `connect.py update` fetches the pack.)*

## Commands

`connect` and `update` ship with the plugin; the rest are **installed on connect**
(they appear as `/listops:*` after the one-time setup + restart).

| Command | Stage |
|---|---|
| `/listops:connect <dra_ key>` | One-time setup: authorize + download the skill pack |
| `/listops:update` | Re-sync the installed skills to the latest version |
| `/listops:build <description + requirements>` | Full pipeline |
| `/listops:plan` | Source payload + schema pack + budget |
| `/listops:list` | LIST + INTAKE via the DRA API |
| `/listops:enrich` | Tiered enrich→filter loop |
| `/listops:filter` | Standalone re-filter (no new spend) |
| `/listops:thesis` | Thesis scoring + ranking |
| `/listops:qa` | Independent QA |
| `/listops:export` | Gap-fill + final deliverable |
| `/listops:status` | Session status, funnel, gates, credits |

Plain language works too ("find founder-owned HVAC companies near Tampa") — the
`list-building` skill triggers on intent.

## What's delivered on connect

The marketplace package contains only the bootstrap (`.mcp.json`, the `connect`/
`update` commands, and `connect.py`). Everything below is served by the DRA API
to valid keys and installed under `~/.claude/` — it is **not** in this repo:

- **Skills**: `list-building` (the planner — candidate acquisition planning,
  enrichment waterfall & down-selection planning, QA planning) and
  `list-operations` (the operator — runs the list/research APIs, combines
  sources + dedupes, creates schemas, executes spend responsibly, performs
  scoring/sorting/down-selection)
- **Agent**: `qa-judge` (independent verification)
- **Scripts**: `session.py` (atomic session tracking), `intake_screen.py`
  (blocklist + dedupe screening), `dedupe.py`, `dra_client.py` (resumable
  batches with credit pre-flight)
- **Assets**: `pe-platforms.txt` (curated PE/franchise blocklist — append as QA
  confirms new ones)
- The `list_companies` API spec for the backend team: `docs/list-method-design.md`
  at the marketplace repo root.
