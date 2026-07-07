#!/usr/bin/env python3
"""LLM curation layer for the weekly refresh (runs after refresh.py).

Reads data/refresh_report.json. For each new unassigned candidate, fetches the
document text from Indian Kanoon and asks Claude to classify it per the
inclusion rule in pipeline/curation.json. For each tracked case with new
orders, fetches the newest order and asks Claude for a gist + significance +
updated latest_development. Applies changes to curation.json, rebuilds the
registry and dashboard, and writes data/curation_log.json.

Degrades gracefully: any API failure logs the error and exits 0 — the
mechanical refresh (new orders with links) has already been published.

Env: ANTHROPIC_API_KEY, IK_API_TOKEN.
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ik_client

ROOT = Path(__file__).resolve().parent.parent
CURATION_PATH = ROOT / "pipeline" / "curation.json"
MODEL = "claude-opus-4-8"

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["track", "notable", "borderline", "ignore"]},
        "reason": {"type": "string"},
        "title": {"type": "string"},
        "case_number": {"type": "string"},
        "case_type": {"type": "string"},
        "status": {"type": "string", "enum": ["pending", "monitoring", "disposed", "unknown"]},
        "filed_year": {"type": "integer"},
        "themes": {"type": "array", "items": {"type": "string"}},
        "why_it_matters": {"type": "string"},
        "gist": {"type": "string"},
        "match_pattern": {"type": "string"},
    },
    "required": ["action", "reason", "title", "case_number", "case_type", "status",
                 "filed_year", "themes", "why_it_matters", "gist", "match_pattern"],
    "additionalProperties": False,
}

GIST_SCHEMA = {
    "type": "object",
    "properties": {
        "gist": {"type": "string"},
        "significance": {"type": "string", "enum": ["major", "routine"]},
        "latest_development": {"type": "string"},
    },
    "required": ["gist", "significance", "latest_development"],
    "additionalProperties": False,
}


def doc_text(tid: int, limit: int = 9000) -> str:
    d = ik_client.doc(tid)
    text = re.sub(r"<[^>]+>", " ", d.get("doc") or "")
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit // 2] + " [...] " + text[-limit // 2:]
    return text


def ask(client, system: str, user: str, schema: dict) -> dict:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": user}],
    )
    text = next(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def norm_pattern(title: str) -> str:
    t = re.sub(r"\s+on\s+\d{1,2}\s+\w+,\s+\d{4}\s*$", "", title)
    t = re.sub(r"[&.,]", "", t).lower()
    t = re.sub(r"\s+(and|ors|anr|etc|others)\b", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.split(" vs ")[0].strip() or t[:40]


def main() -> None:
    report_path = ROOT / "data" / "refresh_report.json"
    if not report_path.exists():
        print("no refresh report — nothing to curate")
        return
    report = json.loads(report_path.read_text())
    candidates = report.get("new_unassigned_candidates", [])
    grew = report.get("cases_with_new_orders", [])
    if not candidates and not grew:
        print("nothing new — no curation needed")
        return

    log = {"date": date.today().isoformat(), "classified": [], "gists": [], "errors": []}
    curation = json.loads(CURATION_PATH.read_text())
    changed = False
    new_case_ids = []

    try:
        import anthropic
        client = anthropic.Anthropic()
    except Exception as e:
        log["errors"].append(f"anthropic client init failed: {e}")
        (ROOT / "data" / "curation_log.json").write_text(json.dumps(log, indent=1))
        print(f"SKIPPED LLM curation: {e}", file=sys.stderr)
        return

    rule = curation["_comment"] if "inclusion" in curation.get("_comment", "") else ""
    inclusion_rule = (
        "Track a case only if it seeks or produces SYSTEMIC relief on road safety in India "
        "(nationwide/statewide directions, guidelines, monitoring, policy change) — PILs, suo motu "
        "matters, Constitution Bench references, appeals with systemic directions. EXCLUDE individual "
        "motor accident compensation appeals, insurance disputes, and criminal appeals UNLESS the "
        "judgment sets precedent every MACT/insurer must follow (then it is 'notable'). "
        "Use 'borderline' for genuinely unclear matters. Use 'ignore' for routine appeals. " + rule
    )

    classify_system = (
        "You curate the Supreme Court Road Safety Litigation Tracker for Crashfree India, a road-safety "
        "non-profit. Classify Supreme Court documents per this rule:\n" + inclusion_rule +
        "\nGround every field in the document text provided — never invent case numbers, benches, or "
        "holdings. If a field is not determinable from the text, use 'unknown' or an empty string. "
        "Keep why_it_matters and gist to 1-2 sentences each, factual and specific. match_pattern must "
        "be a lowercase substring of the case title (petitioner name) usable to match related orders."
    )

    # 1. classify new unassigned candidates
    for c in candidates:
        try:
            text = doc_text(c["tid"])
            result = ask(client, classify_system,
                         f"Document title: {c['title']}\nDate: {c['date']}\n\nFull text (may be truncated):\n{text}",
                         CLASSIFY_SCHEMA)
            entry = {"tid": c["tid"], "date": c["date"], "title": c["title"],
                     "action": result["action"], "reason": result["reason"]}
            log["classified"].append(entry)
            if result["action"] == "track":
                cid = re.sub(r"[^a-z0-9]+", "-", result["match_pattern"])[:40].strip("-") + f"-{c['date'][:4]}"
                curation["tracked_cases"].append({
                    "id": cid,
                    "match": [result["match_pattern"] or norm_pattern(c["title"])],
                    "title": result["title"],
                    "case_number": result["case_number"] or "(verify)",
                    "court": "Supreme Court of India",
                    "case_type": result["case_type"] or "Writ",
                    "status": result["status"] if result["status"] != "unknown" else "pending",
                    "filed_year": result["filed_year"] or int(c["date"][:4]),
                    "themes": result["themes"][:5],
                    "why_it_matters": result["why_it_matters"],
                    "latest_development": f"{c['date']}: {result['gist']}" if result["gist"] else "",
                    "order_notes": {c["date"]: {"gist": result["gist"], "significance": "major"}} if result["gist"] else {},
                })
                new_case_ids.append(cid)
                changed = True
            elif result["action"] == "notable":
                curation["notable_judgments"].append({
                    "tid": c["tid"], "date": c["date"], "title": result["title"],
                    "gist": result["gist"],
                })
                changed = True
            elif result["action"] == "borderline":
                curation["borderline_excluded"].append({"why": result["reason"], "cases": [result["title"]]})
                changed = True
        except Exception as e:
            log["errors"].append(f"classify tid={c.get('tid')}: {e}")

    # 2. gists for tracked cases that grew
    gist_system = (
        "You summarise Supreme Court of India orders for a road-safety litigation tracker. "
        "Write a 1-2 sentence gist of what THIS order does, grounded only in the text. Mark significance "
        "'major' only for substantive directions, judgments, or notable developments — listings, "
        "adjournments, extensions, and exemptions are 'routine' (gist may be empty for those). "
        "latest_development: one sentence, starting with the date, capturing where the case stands now."
    )
    registry = json.loads((ROOT / "data" / "cases.json").read_text())
    by_id = {cs["id"]: cs for cs in registry["cases"]}
    for cid in grew:
        case = by_id.get(cid)
        spec = next((s for s in curation["tracked_cases"] if s["id"] == cid), None)
        if not case or not spec or not case["orders"]:
            continue
        newest = case["orders"][-1]
        try:
            text = doc_text(newest["tid"])
            result = ask(client, gist_system,
                         f"Case: {case['title']} ({case['case_number']})\nOrder date: {newest['date']}\n\nOrder text:\n{text}",
                         GIST_SCHEMA)
            log["gists"].append({"case": cid, "date": newest["date"], **result})
            if result["significance"] == "major" and result["gist"]:
                spec.setdefault("order_notes", {})[newest["date"]] = {
                    "gist": result["gist"], "significance": "major"}
            if result["latest_development"]:
                spec["latest_development"] = result["latest_development"]
            changed = True
        except Exception as e:
            log["errors"].append(f"gist case={cid}: {e}")

    if changed:
        CURATION_PATH.write_text(json.dumps(curation, indent=2, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_registry.py")], check=True)
        # build_registry resets new_this_refresh — restore it (grown cases + newly added)
        registry = json.loads((ROOT / "data" / "cases.json").read_text())
        registry["new_this_refresh"] = sorted(set(grew) | set(new_case_ids))
        registry["meta"]["built"] = date.today().isoformat()
        (ROOT / "data" / "cases.json").write_text(json.dumps(registry, indent=1, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_dashboard.py")], check=True)

    (ROOT / "data" / "curation_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
    print(json.dumps(log, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
