# SC Road Safety Litigation Tracker

Curated tracker of road-safety litigation in the Supreme Court of India — systemic/PIL
matters with order-by-order timelines, plus a notable-judgments feed for precedent-setting
motor accident compensation rulings. High Courts are phase 2 (`court` field exists from day one).

**Owner:** Crashfree India (Vision Zero Trust) · deepanshu@crashfreeindia.org
**Dashboard:** served from `docs/` via GitHub Pages.

## How it runs (fully autonomous)
Every Tuesday 08:10 IST, GitHub Actions ([weekly-refresh.yml](.github/workflows/weekly-refresh.yml)):
1. `pipeline/refresh.py` — searches Indian Kanoon (SC judgments + daily orders, ~40-day window),
   merges new hits, rebuilds registry + dashboard, writes `data/refresh_report.json`
2. `pipeline/auto_curate.py` — Claude (claude-opus-4-8) classifies new candidates per the
   inclusion rule and writes gists for new orders in tracked cases; updates `pipeline/curation.json`
3. Commits and pushes — GitHub Pages redeploys the dashboard automatically

Secrets required: `IK_API_TOKEN` (Indian Kanoon), `ANTHROPIC_API_KEY` (curation).

## Architecture
- `pipeline/ik_client.py` — Indian Kanoon API client (search / doc / docmeta), stdlib + certifi
- `pipeline/seeds.json` — seed cases + discovery query battery
- `pipeline/curation.json` — the human/LLM-curated case metadata (single source of truth)
- `pipeline/directions.json` — the Accountability Ledger: government directions with deadlines
- `pipeline/build_registry.py` — curation + directions + raw hits → `data/cases.json`
- `pipeline/build_dashboard.py` — `data/cases.json` → `docs/index.html` (self-contained, CFI design system)
- `data/raw/_index.json` — all hits ever seen (dedupe state); `_unassigned.json` — audit trail

## The Accountability Ledger
`directions.json` records concrete directions the Court gave a government duty-bearer, each with
the granted period converted to an absolute `due` date. The dashboard computes status LIVE
(overdue / due-soon / upcoming) from `due` vs today, so a deadline flips to overdue on its own
even between refreshes. Explicit `status` (missed/complied/ongoing) overrides the date, and is
set only when a later tracked order confirms it. `auto_curate.py` extracts new deadline-bearing
directions from each major new order weekly. Honesty rule: "deadline passed" ≠ "government failed";
"non-compliance recorded" is used only where the Court's own later order says so.

Rebuild chain after editing curation.json:
`python3 pipeline/build_registry.py && python3 pipeline/build_dashboard.py`

## Data source
Indian Kanoon API (api.indiankanoon.org). Costs: search ₹0.50/page, doc ₹0.20, docmeta ₹0.02.
Weekly refresh ≈ ₹15–20. SC daily orders are `doctypes:scorders`; judgments are `doctypes:supremecourt`.
Note: the API requires POST + a custom User-Agent (Cloudflare bans the default Python UA).

## Inclusion rule (curation boundary)
Track a case if it seeks or produces **systemic relief** (directions, guidelines, monitoring,
policy change) on road safety. Exclude individual compensation appeals unless the ruling
sets precedent (then it goes to `notable_judgments`, not `cases`).

Order gists are working summaries for advocacy tracking, not legal advice; every order links
to its full text on Indian Kanoon.
