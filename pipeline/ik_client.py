#!/usr/bin/env python3
"""Indian Kanoon API client — stdlib only.

The IK API uses HTTP POST for all endpoints, with `Authorization: Token <token>`.
Filters (doctypes:, fromdate:, todate:, title:, cite:) go inside formInput.

Usage:
    python3 ik_client.py search "road safety doctypes:supremecourt" --pages 2
    python3 ik_client.py doc 12345
    python3 ik_client.py docmeta 12345
"""

import argparse
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:  # python.org macOS builds ship without CA certs wired up
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

BASE = "https://api.indiankanoon.org"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def _token() -> str:
    import os
    tok = os.environ.get("IK_API_TOKEN", "")
    if not tok and ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if line.startswith("IK_API_TOKEN="):
                tok = line.split("=", 1)[1].strip()
    if not tok:
        sys.exit("IK_API_TOKEN not set — add it to .env or the environment.")
    return tok


def _post(path: str) -> dict:
    req = urllib.request.Request(
        BASE + path,
        method="POST",
        headers={
            "Authorization": f"Token {_token()}",
            "Accept": "application/json",
            # Cloudflare bans the default Python-urllib UA (error 1010)
            "User-Agent": "crashfree-sc-tracker/1.0",
        },
    )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 2:
                time.sleep(5 * (attempt + 1))
                continue
            body = e.read().decode("utf-8", "replace")[:500]
            sys.exit(f"HTTP {e.code} on {path}: {body}")
    raise RuntimeError("unreachable")


def search(query: str, pagenum: int = 0) -> dict:
    """One page of search results (₹0.50/call). Returns dict with 'docs' list."""
    q = urllib.parse.quote_plus(query)
    return _post(f"/search/?formInput={q}&pagenum={pagenum}")


def search_all(query: str, max_pages: int = 5, delay: float = 1.0) -> list:
    """Collect docs across pages until exhausted or max_pages hit."""
    docs = []
    for page in range(max_pages):
        result = search(query, pagenum=page)
        batch = result.get("docs", [])
        if not batch:
            break
        docs.extend(batch)
        if len(batch) < 10:  # last page
            break
        if page == max_pages - 1:
            # a full final page means results were likely truncated — say so
            # loudly rather than silently under-fetching (matters after gaps)
            print(f"  WARNING: '{query}' hit max_pages={max_pages} with a full "
                  f"page — results may be truncated; found={result.get('found','?')}",
                  file=sys.stderr)
        time.sleep(delay)
    return docs


def doc(docid: int, maxcites: int = 0, maxcitedby: int = 0) -> dict:
    """Full document (₹0.20/call). maxcitedby>0 also returns cases citing this one."""
    extra = ""
    if maxcites:
        extra += f"&maxcites={maxcites}"
    if maxcitedby:
        extra += f"&maxcitedby={maxcitedby}"
    sep = "?" + extra[1:] if extra else ""
    return _post(f"/doc/{docid}/{sep}")


def docmeta(docid: int) -> dict:
    """Metadata only (₹0.02/call) — title, court, date, cites/citedby counts."""
    return _post(f"/docmeta/{docid}/")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--pages", type=int, default=1)

    d = sub.add_parser("doc")
    d.add_argument("docid", type=int)
    d.add_argument("--citedby", type=int, default=0)

    m = sub.add_parser("docmeta")
    m.add_argument("docid", type=int)

    args = ap.parse_args()
    if args.cmd == "search":
        out = search_all(args.query, max_pages=args.pages)
        print(json.dumps(out, indent=2, ensure_ascii=False))
        print(f"\n-- {len(out)} docs --", file=sys.stderr)
    elif args.cmd == "doc":
        print(json.dumps(doc(args.docid, maxcitedby=args.citedby), indent=2, ensure_ascii=False))
    elif args.cmd == "docmeta":
        print(json.dumps(docmeta(args.docid), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
