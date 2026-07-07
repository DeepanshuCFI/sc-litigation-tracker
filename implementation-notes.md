# Implementation Notes — SC Road Safety Litigation Tracker

## Plan status
Approved and implemented 7 Jul 2026 (Parliament-tracker pattern: flat JSON + static dashboard + weekly scheduled task).

## Progress
- [x] Scaffold: README, .env, ik_client.py, seeds.json
- [x] IK API token installed (₹500 dev credit active; non-commercial ₹10k/month tier under review)
- [x] Smoke test (fixed macOS SSL certs via certifi; fixed Cloudflare 1010 with custom User-Agent "crashfree-sc-tracker/1.0")
- [x] Backfill: 3 seed + 12 discovery queries × 2 doctypes (supremecourt + scorders), 567 unique docs, ~₹43
- [x] Curation: 13 tracked cases (179 docs assigned), 8 notable judgments, 5 borderline exclusions, 383 docs in audit file
- [x] Verification pass: 10 key documents fetched; SaveLIFE split into WP(C) 235/2012 (disposed) + WP(C) 726/2024 (pending); Gyan Prakash = WP(C) 1272/2019; Gohar = C.A. 9322/2022 + MA 825/2023 (monitoring)
- [x] Dashboard: dashboard/index.html (self-contained, CFI design tokens), verified in browser
- [x] Weekly refresh: pipeline/refresh.py dry-run clean (30 pages, ₹15, 3 new docs → all correctly unassigned)
- [x] Scheduled task "sc-litigation-tracker-refresh": Tuesdays 08:10 IST

## Key facts
- Indian Kanoon API: POST + `Authorization: Token`; SC daily orders live under doctypes:scorders (97 Rajaseekaran orders there vs 7 in judgments doctype)
- Costs: search ₹0.50/page, doc ₹0.20, docmeta ₹0.02; weekly refresh ≈ ₹15 + occasional doc fetches
- Rebuild chain: curation.json → build_registry.py → cases.json → build_dashboard.py → dashboard/index.html
- refresh.py orchestrates the whole chain + writes data/refresh_report.json for the curation session

## Deviations
- Dashboard eyebrow changed to avoid all-caps brand name (design-system rule)
- Added `monitoring` as a third case status (Gohar Mohammed: disposed but compliance-monitored via MA)

## Open Questions
- GIC v. AP and Ajay Canu case numbers still marked (verify) — cosmetic, order links work
- Notable-judgments feed intentionally small (8 verified); grows via weekly refresh
- Phase 2 (High Courts) not started; data model already carries `court` field
