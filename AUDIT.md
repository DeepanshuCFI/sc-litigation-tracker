# System Audit — SC Road Safety Litigation Tracker

Date: 21 Jul 2026 · Auditor: Claude (session review) · Status: IN PROGRESS — saved incrementally

Scope: full system — GitHub Actions workflow, fetch pipeline (refresh.py / ik_client.py),
LLM curation (auto_curate.py), data model (curation.json / directions.json / cases.json),
build (build_registry.py / build_dashboard.py), dashboard, ops/security.

Ratings: 🔴 fix soon · 🟡 worth improving · 🟢 fine / by design · 💡 addition to consider

---

## 1. Ops & security

- 🔴 **No failure notification.** `weekly-refresh.yml` has no alerting step. If the
  Tuesday run fails (IK outage, Anthropic outage, quota), nobody is told — the Monday
  review task only catches it 6 days later, and only if it checks. Add a final
  `if: failure()` step (or a separate workflow watching `workflow_run`) that emails/
  notifies. GitHub's own "Actions failure" email only goes to the actor who last
  pushed the workflow file — verify Deepanshu actually receives those.
- 🟡 **Actions pin drift.** `actions/checkout@v4`, `setup-python@v5` — fine, but
  `pip install anthropic certifi` is unpinned. An anthropic SDK major-version bump
  (e.g. removal of `output_config` beta shape) would break curation silently on a
  Tuesday. Pin: `pip install "anthropic>=0.40,<1" certifi`, or a requirements.txt.
- 🟡 **Curation "degrades gracefully" into silence.** auto_curate exits 0 on any API
  failure by design (mechanical refresh still publishes). Good — but the job summary
  is the only place errors appear, and nobody reads it unless the run fails. Errors
  in `curation_log.json.errors` should surface in the Monday review prompt (the
  scheduled task reads the log, so: task instruction already covers it — keep).
- 🟢 `.env` correctly gitignored; workflow uses repo secrets; no token in git history.
- 🟢 `concurrency` group + no cancel-in-progress: correct for a commit-pushing job.
- 🟡 **Local vs cloud divergence.** Local working copy is used by the Monday review
  to hot-fix JSON and push. If a manual fix lands between Tuesday runs, fine (pull
  precedes run implicitly via fresh checkout). But local scratch edits left
  uncommitted (e.g. AUDIT.md) will make future `git pull` merges noisier. Keep
  working tree clean after each review session.

## 2. Fetch layer (refresh.py, ik_client.py)

- 🟢 Stdlib-only client, retry on 429/5xx, certifi fallback, UA set — solid.
- 🔴 **`search_all` pagination `found` unused / max_pages=5 cap.** A query returning
  >50 docs in the 40-day window silently truncates: `pages` loop breaks only on
  short page or cap. For weekly deltas 50 is plenty, but after any long gap
  (workflow disabled a month, IK backfills) truncation is silent. Log a warning when
  a query hits max_pages with a full last page.
- 🟡 **`--days-back 40` window vs `fromdate` format.** IK `fromdate:` is DD-MM-YYYY —
  correct here. But if a run fails 3+ weeks running, 40 days may no longer cover the
  gap. The workflow could compute days-back from the last successful
  `refresh_report.json.refresh_date` instead of a constant.
- 🟡 **Cost accounting is approximate and search-only.** `approx_cost_inr = pages*0.5`
  ignores `doc` fetches by auto_curate (₹0.20 each). Minor; fold doc-fetch count into
  the report for honest numbers.
- 🟢 Dedup by tid into `_index.json` with query provenance — good design.

## 3. LLM curation (auto_curate.py)

- 🟢 Structured output via JSON schema; theme enum closed (fixed 21 Jul); recital
  guard prompt + near_duplicate backstop (fixed 21 Jul); extraction decoupled from
  significance (fixed 21 Jul).
- 🔴 **Gist/direction extraction only reads the NEWEST order per grown case**
  (`newest = case["orders"][-1]`). If a case gains TWO orders in one refresh window
  (happens after court vacations), the earlier one gets no gist and its directions
  are never extracted. Loop over all orders newer than the previous latest, not
  just [-1].
- 🟡 **`doc_text` truncates to 9k chars (middle elided).** Long orders (Phalodi April
  order is ~30k) lose their middle — where operative directions often sit after long
  cause lists. The July recital sat in the kept half by luck. Raise limit to ~24k for
  the directions pass (cost is trivial at these volumes) or strip the appearance/
  cause-list header before truncating.
- 🟡 **compute_due month arithmetic**: `n*30.44 days` gives 2026-04-13 + 3 months =
  2026-07-13 ✓ but can drift ±1 day vs calendar months. Courts think in calendar
  months. Use dateutil-free calendar month addition (roll month, clamp day).
- 🟡 **New-case id collision**: `cid = match_pattern[:40] + year`. Two same-year
  cases with similar names collide silently, merging their timelines. Check
  uniqueness against existing ids and suffix -2 if needed.
- 🟡 **match_pattern from LLM drives title-matching forever.** A too-broad pattern
  (e.g. "union of india") would vacuum unrelated docs into a case. Consider a sanity
  check: pattern must appear in the source title, and must be ≥3 words or contain a
  distinctive proper noun.
- 💡 **Order-date ≠ publish-date.** Ledger uses `publishdate` as order_date. IK
  publishdate normally equals the order date for SC daily orders, but delayed
  uploads happen; low risk, note only.

## 4. Data model

- 🟢 curation.json as single human-editable source of truth, directions.json
  separate — clean separation of machine-merge vs human-curate.
- 🔴 **Ledger has no `status: "deadline-passed-pending-affidavit"` middle state —
  by design (neutral computed status). OK — but nothing links a direction to the
  affidavit/compliance EVENT when one arrives.** The 13 Jul order shows the shape:
  Bihar/Karnataka/Puducherry filed. Today that lives in one status_note string. A
  `compliance_events: [{date, tid, note}]` array per direction would let the
  dashboard show "3/36 States filed" style progress without flipping status.
- 🟡 **directions.json id scheme mixed**: hand-authored (`phalodi-20260413-a`) vs
  machine (`{cid}-{yyyymmdd}-{i}`). The `-{i}` index is fragile: if the extractor
  returns directions in a different order on a re-run, ids shift and the
  `did in existing_dir_ids` dedup misfires, appending duplicates. Since
  near_duplicate now guards this, risk is low, but a content-hash id would be
  sturdier.
- 🟡 **`historical: true` flag exists but dashboard treatment unverified** (check §5).
- 🟢 28 directions all conform to closed theme taxonomy (verified 21 Jul).

## 5. Dashboard (build_dashboard.py, docs/)

- 🔴 **Cross-wired filter handlers (CONFIRMED BUG, fixed 21 Jul).** The docket
  handlers bind to ALL `.fbtn` / `.tchip`, including the ledger's. Clicking any
  ledger status filter also fired the docket handler with `data-status` undefined →
  `fStatus=undefined` → `matches()` rejects every case → **all three docket sections
  went empty** until "All cases" was clicked. Ledger authority chips likewise reset
  the docket theme filter and stole `.active` states. Fix: scope selectors to
  `#docket .fbtn` / `#theme-chips .tchip`.
- 🔴 **`next_listing` goes stale (CONFIRMED, fixed for Phalodi 21 Jul).** Four cases
  carry `next_listing`; the curator never updates it. Phalodi displayed "~June 2026"
  while the 13 Jul order lists the matter for **17 Aug 2026**. A tracker showing a
  wrong next hearing date is worse than showing none. Fix: add `next_listing` to
  GIST_SCHEMA so the weekly gist pass refreshes it from the order text ("List on…").
- 🟡 **No "Complied" filter button** in the ledger (complied entries visible only
  under "All directions"), and the green "confirmed complied" stat card isn't
  clickable. Minor.
- 🟡 **`historical: true` is dead data** — set on five 2017/2024 backfilled
  directions, read by nothing. Either render it (e.g. a "standing obligation since
  2017" pill — arguably powerful) or drop the flag.
- 🟡 **Timezone**: ledger status computed in the viewer's local timezone; an IST
  deadline can show "due soon" a few hours longer for a US viewer. Cosmetic.
- 🟡 **Google Fonts dependency** — fine on GH Pages, but the page renders in
  fallback fonts offline/in restrictive networks. Acceptable.
- 🟢 XSS surface: titles tag-stripped at build; `</` escaped in the JSON island;
  content is pipeline-authored. Low risk.
- 🟢 Design-system compliance, 44px touch targets, jumpnav, honest ledger-note
  language — all good. The "not a finding of government failure" footnote is
  exactly the right legal-comms posture.

## 6. Coverage & product

- 🟢 23 discovery queries × 2 doctypes is a wide net; pedestrian/right-to-walk
  additions post-launch prove the sweep works.
- 💡 **Query gaps worth adding** (cheap, ₹0.50/page/week each):
  - `"electric vehicle" OR "e-rickshaw" safety doctypes:supremecourt` — emerging docket
  - `"school bus" OR "school children" transport safety` — recurring SC theme
  - `"drunk driving" OR "drunken driving"` — enforcement docket
  - `"National Highway" death OR fatality directions` — catches highway suo motus the
    "road safety" phrase misses
  - `"protection of good samaritan"` variant spelling; `"trauma centre"` post-crash
- 💡 **Case-number search.** Discovery is title/phrase-only. IK supports citation
  search; tracked pending cases could be polled by case number (`title:` operator on
  the cause-title) to catch orders whose text uses none of the seed phrases. The
  Madhabi Das false-candidate route (phrase match) already works; the inverse
  (order in a tracked case matching no phrase) is the silent-miss risk. Mitigated by
  seed_cases queries for the big three; not for newer tracked cases (Phalodi has no
  seed query — a Phalodi order that says "highway" but not "road safety" could slip
  a week's sweep; it would be caught later by the 40-day overlap only if a phrase
  eventually matches).
  → RECOMMENDED: add one seed query per pending tracked case (title-based).
- 💡 **Compliance-events model** (see §4): the Phalodi affidavit trickle
  (3/36 filed) is the story of the case right now, and the ledger can't express it.
- 💡 **RSS/JSON feed of ledger flips.** The dashboard recomputes overdue live, but
  nobody is notified when a direction crosses its due date. A tiny weekly diff in
  the job summary ("newly overdue this week: …") — or in the Monday review — would
  make the ledger actionable, which is its whole point. The Monday scheduled task
  could compute this from `due` dates alone.
- 💡 **High Courts phase 2** (README promise): `court` field exists; IK doctypes
  support HC filtering. Big scope step — defer deliberately, not accidentally.
- 🟢 README and implementation-notes are accurate post-21-Jul fixes.

## Priority summary

| # | Item | Type | Status |
|---|------|------|--------|
| 1 | Dashboard filter cross-wiring emptied docket | 🔴 bug | **fixed 21 Jul** |
| 2 | Stale `next_listing` (wrong hearing date shown) | 🔴 bug | **fixed + schema'd 21 Jul** |
| 3 | Workflow failure notification | 🔴 ops | open — needs repo settings or a notify step |
| 4 | Multi-new-order gap (only newest order curated) | 🔴 pipeline | open |
| 5 | Unpinned `anthropic` dependency | 🟡 ops | open — one-line fix |
| 6 | doc_text 9k truncation on long orders | 🟡 pipeline | open |
| 7 | Seed query per tracked pending case | 💡 coverage | open |
| 8 | Compliance-events per direction (affidavit trickle) | 💡 model | open |
| 9 | "Newly overdue this week" in weekly summary | 💡 product | open |
| 10 | Calendar-month due-date arithmetic | 🟡 pipeline | open |

Items 3–6 are each ≤30 min. Items 7–9 are the next real product increments.

