#!/usr/bin/env python3
"""Citation-follow discovery sweep (run quarterly, ~Rs 2 in API calls).

Phrase-based discovery misses cases that never use a seed phrase in their
text. This sweep walks the OTHER edge of the citation graph: for each
principal systemic order in seeds.json -> citation_follow, fetch the cases
that CITE it (doc endpoint with maxcitedby) and surface any Supreme Court
document not already in the raw index. Findings go to
data/citation_sweep_report.json for the operator to classify — this script
never writes to curation.json itself.

Usage: python3 pipeline/citation_sweep.py [--maxcitedby N]   (default 50)
"""

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ik_client

ROOT = Path(__file__).resolve().parent.parent


def clean(t: str) -> str:
    return re.sub(r"<[^>]+>", "", t or "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--maxcitedby", type=int, default=50)
    args = ap.parse_args()

    seeds = json.loads((ROOT / "pipeline" / "seeds.json").read_text())
    follow = seeds.get("citation_follow", {}).get("docids", [])
    if not follow:
        sys.exit("seeds.json has no citation_follow.docids")

    index = json.loads((ROOT / "data" / "raw" / "_index.json").read_text())
    known = set(index.keys())
    curation = json.loads((ROOT / "pipeline" / "curation.json").read_text())
    match_by_case = {t["id"]: t["match"] for t in curation["tracked_cases"]}

    def norm(t: str) -> str:
        t = clean(t).lower()
        t = re.sub(r"[&.,]", "", t)
        t = re.sub(r"\s+(and|ors|anr|etc|others)\b", "", t)
        return re.sub(r"\s+", " ", t).strip()

    findings, errors = [], []
    seen_this_run = set()
    probes = fetches = 0
    for f in follow:
        # IK often indexes the same judgment under several tids (court copy vs
        # canonical), and the citation graph hangs off the canonical one. Sweep
        # every same-date tid in our index whose title matches the case.
        variants = {f["tid"]}
        for tid_s, doc_meta in index.items():
            if doc_meta.get("publishdate") == f["date"] and any(
                    m in norm(doc_meta.get("title", ""))
                    for m in match_by_case.get(f["case_id"], [])):
                variants.add(doc_meta["tid"])
        for tid in sorted(variants):
            try:
                probes += 1
                time.sleep(0.3)
                if not ik_client.docmeta(tid).get("numcitedby"):  # Rs 0.02 probe
                    continue
                fetches += 1
                d = ik_client.doc(tid, maxcitedby=args.maxcitedby)
            except (SystemExit, OSError) as e:  # hard HTTP errors / timeouts
                errors.append(f"tid={tid}: {e}")
                continue
            for c in d.get("citedby") or []:
                ctid = str(c.get("tid"))
                title = clean(c.get("title", ""))
                if ctid in known or ctid in seen_this_run:
                    continue
                seen_this_run.add(ctid)
                # citedby entries carry no docsource — resolve the court via a
                # cheap docmeta probe; HC citations are out of scope (SC only)
                try:
                    probes += 1
                    time.sleep(0.3)
                    source = ik_client.docmeta(ctid).get("docsource", "")
                except (SystemExit, OSError) as e:
                    errors.append(f"docmeta ctid={ctid}: {e}")
                    continue
                if "supreme court" not in source.lower():
                    continue
                findings.append({
                    "tid": c.get("tid"),
                    "title": title,
                    "docsource": source,
                    "cites": {"case_id": f["case_id"], "order_date": f["date"], "tid": tid},
                })
            time.sleep(0.5)

    report = {
        "sweep_date": date.today().isoformat(),
        "docids_followed": len(follow),
        "maxcitedby": args.maxcitedby,
        "new_sc_candidates": findings,
        "errors": errors,
        "approx_cost_inr": round(probes * 0.02 + fetches * 0.20, 2),
    }
    (ROOT / "data" / "citation_sweep_report.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False))
    print(json.dumps(report, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
