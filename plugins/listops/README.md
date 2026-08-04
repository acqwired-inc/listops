# ListOps

Investment-grade company list building for Claude Code, powered by the Acqwired
Research platform (DRA). Turn a one-line request — *"commercial landscape
maintenance companies within 90 miles of these addresses, owner-operated, >$5M,
no PE"* — into a screened, enriched, thesis-ranked export.

**Discovery runs through the DRA `submit_company_list` API, never through Claude
web search.** Live sources in v1 are **Google Maps** (POI) and **Exa** (neural);
Yelp, Foursquare, and Tavily are accepted but not yet implemented (they return
zero hits with a `not_implemented` per-source error — don't plan to depend on
them). Claude skills supply the intelligence: which sources, keywords, locations,
radii, schemas, filters, and thesis.

## Pipeline

```
CONTEXT → PLAN → LIST → INTAKE SCREEN → [no requirements? → export offer]
        → (ENRICH tier → FILTER)×N → THESIS → QA → GAP-FILL → VERIFY BASICS
        → EXPORT → CONFLICT CHECK (user-run) → CONTACTS (opt-in)
```

| Stage | What happens |
|---|---|
| **Context** | When a buyer is named: research the backer + platform portco → master thesis doc + buy-box → seed the plan |
| **Plan** | Geography-first (POI tiling) or description-first (neural queries) source payload, schema pack with explicit pass/fail rules, thesis text, reserved QA probes, credit budget |
| **List** | `submit_company_list` → poll → `companies.jsonl` with per-source provenance; the curated PE blocklist is applied server-side at discovery (`summary.blocked[]`) |
| **Intake screen** | Free local screening: dedupe, optional org/project extra-blocklist, category sanity, website-gap flags |
| **Enrich + Filter (tiered)** | Tier 1 runs as a 50-100 pilot with a **required stack-ranked manual review gate** (≥90% accuracy before the pool commits); schemas ordered by kill-rate per credit; each tier credit-gated; confidence <50 = data gap, not rejection |
| **Thesis** | `completeCompanyProfile` + thesis text on survivors → rank by `thesis_fit_score` |
| **QA** | Independent judge: spot-checks, mandatory ownership re-verification, coverage probes via the list API |
| **Gap-fill + Verify + Export** | `reconstruct`-first field completion → deterministic basics verification (website liveness, HQ reconciliation, legal name — export blocks on issues) → `final.csv` with provenance + confidence |
| **Conflict check** | User-run: finalist list goes through the org's internal conflict process; never auto-passes |
| **Contacts** | Strictly opt-in, always last: ownership-level leadership + LinkedIn + email/phone for cleared companies only |

Every run is tracked in **`lists/<slug>/session-tracking-<id>.json`** (atomic
writes) — any session or command resumes exactly where the last one stopped.

## Setup

This plugin is a **thin bootstrap** — a connector and a hook, and no commands of its
own. The skills, pipeline commands, and the QA agent are **not shipped in the
marketplace**; they're **downloaded from the DRA API**, gated by a valid
(org-validated) key, and written under `~/.claude/`. The proprietary logic never
sits in a public repo.

1. Install the plugin (marketplace README one level up). The bundled `.mcp.json`
   wires the `evergreen` MCP server.
2. **Authorize the connector** — `/mcp` → `listops` → Authenticate. A browser opens;
   paste your key from the Acqwired dashboard (Settings → API key) once.
3. **Restart Claude Code once.** The `SessionStart` hook reads the credential OAuth just
   stored and installs the pack; the commands and agent load on the following start.
   Then `/listops:status` confirms.

There is deliberately no second key prompt. DRA's authorization server is
bring-your-own-key — the access token it issues **is** your `dra_` key — so once the
connector is authorized the credential is already on disk and the hook just uses it.
It also self-updates: each session start compares the installed pack against the server
and re-downloads only on a change.

**Headless / CI / no browser?** Export `DRA_API_KEY=dra_...` in the environment. The
hook falls back to it when there is no OAuth credential to read, so the pack installs
and self-updates exactly the same way — no command to run.

Requires Python 3.8+ on PATH (the bootstrap script is stdlib-only). `connect.py` also
exposes `set`/`update`/`check`/`clear` as a manual escape hatch if you ever need to
drive it by hand.

## Commands

Every command below is **installed by the hook**, not shipped in the marketplace — they
appear as `/listops:*` once the connector is authorized and you restart.

| Command | Stage |
|---|---|
| `/listops:build <description + requirements>` | Full pipeline |
| `/listops:plan` | Source payload + schema pack + budget |
| `/listops:list` | LIST + INTAKE via the DRA API |
| `/listops:enrich` | Tiered enrich→filter loop |
| `/listops:filter` | Standalone re-filter (no new spend) |
| `/listops:thesis` | Thesis scoring + ranking |
| `/listops:qa` | Independent QA |
| `/listops:export` | Gap-fill + verify basics + final deliverable |
| `/listops:conflict-check` | Hand finalists to your internal conflict process; record exclusions |
| `/listops:contacts` | Opt-in leadership contacts for cleared companies |
| `/listops:status` | Session status, funnel, gates, credits + pack-update nudge |

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
  (dedupe + extra-blocklist screening), `dedupe.py`, `dra_client.py` (resumable
  batches with credit pre-flight + pack-version check), `filter_score.py`
  (config-driven filtering + stack-ranked review CSV), `verify_basics.py`
  (deterministic website/HQ/legal-name verification), `merge_external.py`
  (join the org's own data as free enrichments)

The curated PE/franchise blocklist is applied **server-side at discovery** and
no longer ships to client machines; projects keep a local `blocklist-extra.txt`
for org-specific additions.

## Operating principles

- **Human in the loop before money moves.** Every enrichment tier is
  credit-gated; tier 1 pilots on a 50-100 sample and the full pool never
  commits without a reviewed, recorded gate. The pipeline never pulls
  contacts, runs profiles, or expands scope unprompted.
- **Basic facts are never wrong in a deliverable.** Websites are
  liveness-checked, HQ is reconciled between sources, and legal names come
  from verified profiles — the export blocks on unresolved issues.
- **Everything is auditable.** Sessions record every stage, gate, and credit
  decision; provenance and confidence survive to the final CSV; low-confidence
  values export blank with a named gap, never as facts.
