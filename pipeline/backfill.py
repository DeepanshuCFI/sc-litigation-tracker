#!/usr/bin/env python3
"""One-time backfill: run seed + discovery searches, save raw hits, dedupe.

Writes data/raw/<slug>.json per query and data/raw/_index.json (docid -> summary).
Search cost: ₹0.50/page. Prints a running tally.
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ik_client

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SEEDS = json.loads((ROOT / "pipeline" / "seeds.json").read_text())


def slugify(q: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", q.lower()).strip("-")[:60]


def run_query(query: str, max_pages: int, searches_done: list) -> list:
    docs = ik_client.search_all(query, max_pages=max_pages, delay=1.0)
    pages_used = max(1, (len(docs) + 9) // 10) if docs else 1
    searches_done.append(pages_used)
    out = RAW / f"{slugify(query)}.json"
    out.write_text(json.dumps({"query": query, "docs": docs}, indent=1, ensure_ascii=False))
    print(f"  {len(docs):4d} docs  {query}")
    return docs


def main() -> None:
    searches_done: list = []
    index: dict = {}

    def absorb(docs, source_query):
        for d in docs:
            tid = str(d.get("tid"))
            if tid not in index:
                index[tid] = {
                    "tid": d.get("tid"),
                    "title": d.get("title"),
                    "publishdate": d.get("publishdate"),
                    "docsource": d.get("docsource"),
                    "headline": (d.get("headline") or "")[:400],
                    "citation": d.get("citation"),
                    "queries": [],
                }
            index[tid]["queries"].append(source_query)

    print("== Seed case queries ==")
    for case in SEEDS["seed_cases"]:
        for q in case["search_queries"]:
            absorb(run_query(q, max_pages=15, searches_done=searches_done), q)

    print("== Discovery battery ==")
    for q in SEEDS["discovery_queries"]:
        absorb(run_query(q, max_pages=5, searches_done=searches_done), q)

    (RAW / "_index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False))
    total_pages = sum(searches_done)
    print(f"\nUnique docs: {len(index)}")
    print(f"Search pages used: {total_pages}  (~₹{total_pages * 0.5:.0f})")


if __name__ == "__main__":
    main()
