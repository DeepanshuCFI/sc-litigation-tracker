#!/usr/bin/env python3
"""Build data/cases.json from raw search hits + curation.json.

Assignment: normalized doc title matched against each tracked case's `match`
substrings. Same-date duplicates within a case (judgment + daily-order copies)
collapse to one timeline entry, preferring the judgments doctype.
Unassigned docs are written to data/raw/_unassigned.json for audit.
"""

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
CURATION = json.loads((ROOT / "pipeline" / "curation.json").read_text())


def norm_title(t: str) -> str:
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"\s+on\s+\d{1,2}\s+\w+,\s+\d{4}\s*$", "", t)
    t = re.sub(r"[&.,]", "", t).lower()
    t = re.sub(r"\s+(and|ors|anr|etc|others)\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


def clean(t: str) -> str:
    return re.sub(r"<[^>]+>", "", t or "")


def main() -> None:
    index = json.loads((RAW / "_index.json").read_text())
    existing = {}
    out_path = ROOT / "data" / "cases.json"
    if out_path.exists():
        existing = {
            (c["id"], o["date"]): o
            for c in json.loads(out_path.read_text()).get("cases", [])
            for o in c.get("orders", [])
        }

    cases, unassigned = [], []
    assigned_tids = set()

    for spec in CURATION["tracked_cases"]:
        dmin = spec.get("date_min", "0000")
        dmax = spec.get("date_max", "9999")
        hits = [
            d for d in index.values()
            if any(m in norm_title(d["title"]) for m in spec["match"])
            and dmin <= (d.get("publishdate") or "?") <= dmax
        ]
        for d in hits:
            assigned_tids.add(str(d["tid"]))
        # collapse same-date duplicates, prefer judgment doctype (docsource has no 'Daily Order')
        by_date: dict = {}
        for d in sorted(hits, key=lambda x: (x.get("docsource") or "")):
            dt = d.get("publishdate") or "?"
            if dt not in by_date:
                by_date[dt] = d
        notes = spec.get("order_notes", {})
        orders = []
        for dt in sorted(by_date):
            d = by_date[dt]
            prev = existing.get((spec["id"], dt), {})
            note = notes.get(dt, {})
            orders.append({
                "date": dt,
                "tid": d["tid"],
                "link": f"https://indiankanoon.org/doc/{d['tid']}/",
                "gist": note.get("gist") or prev.get("gist", ""),
                "significance": note.get("significance") or prev.get("significance", "routine"),
            })
        case = {k: v for k, v in spec.items()
                if k not in ("match", "date_min", "date_max", "order_notes")}
        case["orders"] = orders
        case["order_count"] = len(orders)
        case["first_order"] = orders[0]["date"] if orders else None
        case["latest_order"] = orders[-1]["date"] if orders else None
        cases.append(case)

    for tid_s, d in index.items():
        if tid_s not in assigned_tids:
            unassigned.append({
                "tid": d["tid"], "date": d.get("publishdate"),
                "title": clean(d["title"]), "queries": sorted(set(d["queries"])),
            })

    notable = []
    for nj in CURATION["notable_judgments"]:
        notable.append({**nj, "link": f"https://indiankanoon.org/doc/{nj['tid']}/"})

    registry = {
        "meta": {
            "built": date.today().isoformat(),
            "source": "Indian Kanoon API (doctypes: supremecourt + scorders)",
            "raw_docs": len(index),
            "assigned_docs": len(assigned_tids),
        },
        "cases": cases,
        "notable_judgments": sorted(notable, key=lambda x: x["date"], reverse=True),
        "borderline_excluded": CURATION["borderline_excluded"],
        "new_this_refresh": [],
    }
    out_path.write_text(json.dumps(registry, indent=1, ensure_ascii=False))
    (RAW / "_unassigned.json").write_text(json.dumps(unassigned, indent=1, ensure_ascii=False))

    print(f"cases.json: {len(cases)} cases, {len(notable)} notable judgments")
    for c in cases:
        print(f"  {c['order_count']:4d} orders  {c['first_order']} → {c['latest_order']}  [{c['status']:8s}]  {c['title'][:60]}")
    print(f"unassigned: {len(unassigned)} docs (audit file written)")


if __name__ == "__main__":
    main()
