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
- [x] CLOUD MIGRATION (7 Jul 2026): public repo DeepanshuCFI/sc-litigation-tracker; GitHub Actions weekly refresh (Tue 02:40 UTC) with Claude curation (auto_curate.py, claude-opus-4-8); dashboard on GitHub Pages at https://deepanshucfi.github.io/sc-litigation-tracker/ (main:/docs); secrets IK_API_TOKEN + ANTHROPIC_API_KEY encrypted in repo. First cloud run green (0 new docs, ₹15).
- [x] Dashboard grouped: PIL/suo motu (original jurisdiction) vs Appeals & References
- [x] Local scheduled task repurposed: Tuesdays 08:30 IST reviewer (pull, QC the LLM curation, report to Deepanshu) — runs only when the app is open, which is fine; the cloud does the real work

## Key facts
- Indian Kanoon API: POST + `Authorization: Token`; SC daily orders live under doctypes:scorders (97 Rajaseekaran orders there vs 7 in judgments doctype)
- Costs: search ₹0.50/page, doc ₹0.20, docmeta ₹0.02; weekly refresh ≈ ₹15 + occasional doc fetches
- Rebuild chain: curation.json → build_registry.py → cases.json → build_dashboard.py → dashboard/index.html
- refresh.py orchestrates the whole chain + writes data/refresh_report.json for the curation session

- [x] Same-day expansions (7 Jul, on Deepanshu's asks): Shishupal v. Surjeet (₹30k/month homemaker head) in docket + precedent feed; pedestrian sweep → Re: Fundamental Right to Walk and Footpath tracked (2026 INSC 647), Rajaseekaran 14-05-2025 Art-21 footpath order annotated, Baby Sakshi Greola precedent, Raturi + encroachment line on watchlist; battery now 23 queries. Registry: 18 cases / 186 orders / 27 precedents.
- [x] Design-system compliance pass vs CFI_Skill v2.2: all colors token-derived (color-mix), CTA trailing arrows, 22% hero glow, 44px touch targets, exact max-widths, verified at 375/768/1280. Card radius settled at 16px (real rounded-2xl rendering; spec's "12px" prose is a slip) — Deepanshu delegated the call 7 Jul 2026.

## Deviations
- Dashboard eyebrow changed to avoid all-caps brand name (design-system rule)
- Added `monitoring` as a third case status (Gohar Mohammed: disposed but compliance-monitored via MA)

## Open Questions
- GIC v. AP and Ajay Canu case numbers still marked (verify) — cosmetic, order links work
- Notable-judgments feed intentionally small (8 verified); grows via weekly refresh
- Phase 2 (High Courts) not started; data model already carries `court` field
