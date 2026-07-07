#!/usr/bin/env python3
"""Weekly refresh: search for new SC orders/judgments since the last refresh,
merge into the raw index, rebuild the registry and dashboard, and report
what changed so the operator (Claude session) can curate.

Usage: python3 refresh.py [--days-back N]   (default 40 — covers weekly cadence
plus Indian Kanoon's indexing lag with generous overlap; dedup makes re-fetch harmless)
"""

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ik_client

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SEEDS = json.loads((ROOT / "pipeline" / "seeds.json").read_text())


def all_queries() -> list:
    qs = [q for c in SEEDS["seed_cases"] for q in c["search_queries"]]
    qs += SEEDS["discovery_queries"]
    both = []
    for q in qs:
        both.append(q)
        both.append(q.replace("doctypes:supremecourt", "doctypes:scorders"))
    return both


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days-back", type=int, default=40)
    args = ap.parse_args()

    fromdate = (date.today() - timedelta(days=args.days_back)).strftime("%d-%m-%Y")
    index = json.loads((RAW / "_index.json").read_text())
    before_tids = set(index.keys())
    old_reg = json.loads((ROOT / "data" / "cases.json").read_text())
    old_counts = {c["id"]: c["order_count"] for c in old_reg["cases"]}

    pages = 0
    new_docs = []
    for q in all_queries():
        full_q = f"{q} fromdate:{fromdate}"
        try:
            docs = ik_client.search_all(full_q, max_pages=5, delay=1.0)
        except SystemExit as e:
            print(f"  QUERY FAILED (continuing): {full_q}: {e}", file=sys.stderr)
            continue
        pages += max(1, (len(docs) + 9) // 10)
        for d in docs:
            tid = str(d.get("tid"))
            if tid not in index:
                index[tid] = {
                    "tid": d.get("tid"), "title": d.get("title"),
                    "publishdate": d.get("publishdate"), "docsource": d.get("docsource"),
                    "headline": (d.get("headline") or "")[:400],
                    "citation": d.get("citation"), "queries": [],
                }
                new_docs.append(index[tid])
            if q not in index[tid]["queries"]:
                index[tid]["queries"].append(q)
        time.sleep(0.5)

    (RAW / "_index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False))

    # rebuild registry (preserves existing gists via its merge logic)
    subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_registry.py")], check=True)

    # flag cases whose timelines grew
    reg = json.loads((ROOT / "data" / "cases.json").read_text())
    grew = [c["id"] for c in reg["cases"] if c["order_count"] > old_counts.get(c["id"], 0)]
    reg["new_this_refresh"] = grew
    reg["meta"]["built"] = date.today().isoformat()
    (ROOT / "data" / "cases.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False))

    # rebuild dashboard
    subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_dashboard.py")], check=True)

    # operator report
    def ctitle(t):
        return re.sub(r"<[^>]+>", "", t or "")
    assigned = {str(o["tid"]) for c in reg["cases"] for o in c["orders"]}
    unassigned_new = [d for d in new_docs if str(d["tid"]) not in assigned]
    report = {
        "refresh_date": date.today().isoformat(),
        "fromdate_window": fromdate,
        "search_pages": pages,
        "approx_cost_inr": round(pages * 0.5, 1),
        "new_docs_total": len(new_docs),
        "cases_with_new_orders": grew,
        "new_unassigned_candidates": [
            {"tid": d["tid"], "date": d["publishdate"], "title": ctitle(d["title"]),
             "headline": ctitle(d.get("headline") or "")[:200]}
            for d in sorted(unassigned_new, key=lambda x: x.get("publishdate") or "")
        ],
    }
    (ROOT / "data" / "refresh_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
