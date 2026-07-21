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
        "next_listing": {"type": "string"},
    },
    "required": ["gist", "significance", "latest_development", "next_listing"],
    "additionalProperties": False,
}

# Closed taxonomy for ledger directions — keeps the Accountability Ledger's theme
# tags consistent instead of minting a new one-off tag per order.
LEDGER_THEMES = ["institutions", "highways", "enforcement", "post-crash care",
                 "road engineering", "good samaritan", "PM RAHAT",
                 "victim compensation", "driver licensing", "vehicle safety"]

DIRECTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "directions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "directive": {"type": "string"},
                    "authority": {"type": "string"},
                    "granted": {"type": "string"},
                    "theme": {"type": "string", "enum": LEDGER_THEMES},
                },
                "required": ["directive", "authority", "granted", "theme"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["directions"],
    "additionalProperties": False,
}


_STOP = {"the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "at", "by", "with",
         "shall", "any", "all", "every", "be", "is", "are", "within", "from", "this", "that",
         "such", "which", "as", "its", "their", "no", "not", "may", "must", "each"}

# Terms that recur across nearly every direction in this corpus. They carry no
# signal for telling two road-safety directions apart and, on short directives,
# inflate the overlap ratio enough to collide unrelated obligations.
_BOILERPLATE = {"road", "safety", "state", "states", "national", "highway", "highways",
                "court", "india", "union", "territories", "territory", "order", "orders",
                "direction", "directions", "every", "concerned", "authority", "authorities"}


def _content_words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower())
            if w not in _STOP and w not in _BOILERPLATE and len(w) > 2}


def near_duplicate(directive: str, case_id: str, existing: list,
                   threshold: float = 0.4, floor: int = 4):
    """Return the id of an existing direction in the same case that this directive
    restates, else None. Guards against prior directions recited in a later order
    being re-extracted with a fresh (and therefore wrong) deadline clock.

    Tuned on the 13 Jul 2026 Phalodi order, which recited eight already-ledgered
    directions: catches 7 of 8 with no false positive anywhere in the ledger. The
    floor stops two short directives from matching on a handful of shared words."""
    words = _content_words(directive)
    if not words:
        return None
    for d in existing:
        if d.get("case_id") != case_id:
            continue
        other = _content_words(d.get("directive", ""))
        if not other:
            continue
        # containment, not symmetric overlap: a condensed restatement of a longer
        # direction (or vice versa) should still register as the same obligation.
        shared = len(words & other)
        if shared >= floor and shared / min(len(words), len(other)) >= threshold:
            return d["id"]
    return None


def _add_months(d, n: int):
    """Calendar-month addition, day clamped to month end (courts count calendar
    months: 13 Apr + 3 months = 13 Jul, not 13 Apr + 91.32 days)."""
    import calendar
    y, m = divmod(d.month - 1 + n, 12)
    y, m = d.year + y, m + 1
    return d.replace(year=y, month=m, day=min(d.day, calendar.monthrange(y, m)[1]))


def compute_due(order_date: str, granted: str):
    """order_date (ISO) + a granted period like '60 days'/'3 months'/'6 weeks' -> ISO due date.
    Returns None for recurring/unclear periods (those become 'ongoing')."""
    from datetime import date as _date, timedelta
    g = granted.lower().strip()
    m = re.search(r"(\d+)\s*(day|week|month|year)", g)
    if not m:
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "six": 6, "eight": 8, "nine": 9, "twelve": 12}
        m2 = re.search(r"(one|two|three|four|six|eight|nine|twelve)\s*(day|week|month|year)", g)
        if not m2:
            return None
        n, unit = words[m2.group(1)], m2.group(2)
    else:
        n, unit = int(m.group(1)), m.group(2)
    d = _date.fromisoformat(order_date)
    if unit == "day":
        d += timedelta(days=n)
    elif unit == "week":
        d += timedelta(weeks=n)
    elif unit == "month":
        d = _add_months(d, n)
    elif unit == "year":
        d = _add_months(d, 12 * n)
    return d.isoformat()


DOC_FETCHES = {"n": 0}  # for honest cost reporting in the curation log


def doc_text(tid: int, limit: int = 24000) -> str:
    """Fetch and flatten an order. The limit is generous — SC orders put their
    operative directions after pages of appearances, and a tight middle-elision
    (the old 9k) risked cutting exactly the part the ledger needs."""
    DOC_FETCHES["n"] += 1
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


def norm_title(t: str) -> str:
    """Mirror of build_registry.norm_title — the string match patterns run against."""
    t = re.sub(r"<[^>]+>", "", t or "")
    t = re.sub(r"\s+on\s+\d{1,2}\s+\w+,\s+\d{4}\s*$", "", t)
    t = re.sub(r"[&.,]", "", t).lower()
    t = re.sub(r"\s+(and|ors|anr|etc|others)\b", "", t)
    return re.sub(r"\s+", " ", t).strip()


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
                # match_pattern drives title-matching forever — sanity-check it
                # against the source title so a hallucinated or over-broad
                # pattern can't vacuum unrelated documents into the case
                pattern = result["match_pattern"] or ""
                if pattern not in norm_title(c["title"]) or len(pattern) < 8:
                    pattern = norm_pattern(c["title"])
                cid = re.sub(r"[^a-z0-9]+", "-", pattern)[:40].strip("-") + f"-{c['date'][:4]}"
                taken = {s["id"] for s in curation["tracked_cases"]}
                while cid in taken:  # same-year name collision — never merge timelines silently
                    cid += "-x"
                curation["tracked_cases"].append({
                    "id": cid,
                    "match": [pattern],
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
        "Judge the order by what IT adds, not by the length of any earlier order it reproduces: an order "
        "whose operative content is merely re-circulating or reproducing directions already issued on an "
        "earlier date is 'routine'. An order that records non-compliance, sets a fresh deadline, or "
        "threatens coercive consequences (personal appearance, contempt) is 'major' even if short. "
        "latest_development: one sentence, starting with the date, capturing where the case stands now. "
        "next_listing: the next hearing date exactly as the order states it (e.g. 'List on 17th August, "
        "2026' -> '17 August 2026'); empty string if the order fixes no date."
    )
    # Accountability Ledger extraction (grounded, deadline-bearing directions only)
    dir_system = (
        "You extract COMPLIANCE DIRECTIONS from a Supreme Court of India road-safety order for an "
        "accountability ledger. Return only concrete directions that (a) command a government body to DO "
        "something and (b) carry a time period (e.g. 'within 60 days', 'three months', 'six weeks'). "
        "Skip directions with no deadline, adjournments, and anything not addressed to a government "
        "duty-bearer.\n\n"
        "CRITICAL — extract only directions THIS order itself issues. Supreme Court orders routinely "
        "reproduce the directions of an EARLIER order before adding their own. Any block that is quoted "
        "(inside quotation marks), or introduced by wording such as 'vide order dated X this Court issued "
        "the following directions', 'in terms of the order dated X', 'the directions issued earlier were', "
        "or is otherwise recited in the past tense as something already directed on a previous date, is "
        "HISTORY, not a new direction — ignore it entirely, however long and detailed it is. Such recitals "
        "are already in the ledger under their original order date, and re-extracting them here would "
        "wrongly restart their deadline clocks. Read past the recital to the paragraphs where the Court "
        "speaks in the present ('we direct', 'it is directed', 'shall file within') and extract only "
        "those. A long order can legitimately yield zero new directions.\n\n"
        "For each: 'directive' = one grounded sentence (condensed from the text, never "
        "invented); 'authority' = the single primary duty-bearer, normalised to one of MoRTH, NHAI, "
        "States / UTs, District Magistrates, Highway Administrations, State Police, Union (Health), or a "
        "short proper name if none fit; 'granted' = the period exactly as stated (e.g. '60 days'); "
        "'theme' = the closest tag from the fixed list in the schema. "
        "Return an empty list if the order carries no deadline-bearing directions of its own."
    )
    DIR_PATH = ROOT / "pipeline" / "directions.json"
    dirdata = json.loads(DIR_PATH.read_text())
    existing_dir_ids = {d["id"] for d in dirdata["directions"]}
    dir_changed = False

    registry = json.loads((ROOT / "data" / "cases.json").read_text())
    by_id = {cs["id"]: cs for cs in registry["cases"]}
    for cid in grew:
        case = by_id.get(cid)
        spec = next((s for s in curation["tracked_cases"] if s["id"] == cid), None)
        if not case or not spec or not case["orders"]:
            continue
        # gist/extract EVERY order added this refresh, not just the newest —
        # after court vacations a case routinely gains 2+ orders in one window,
        # and skipping the earlier ones left their directions out of the ledger.
        # Chronological order, so the newest order wins latest_development.
        n_new = max(1, report.get("new_order_counts", {}).get(cid, 1))
        for newest in case["orders"][-n_new:]:
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
            # keep next_listing current — a stale hearing date is worse than none
            if result.get("next_listing"):
                spec["next_listing"] = f"{result['next_listing']} (per order of {newest['date']})"
            elif "next_listing" in spec:
                # order fixed no date; drop the old one rather than display it stale
                del spec["next_listing"]
            changed = True

            # Extract deadline-bearing directions from this order into the ledger.
            # Deliberately NOT gated on significance: a procedurally 'routine' listing
            # order can still set a real deadline, and dropping it would leave a hole
            # in the ledger. The extractor returns [] when there is nothing to capture.
            dres = ask(client, dir_system,
                       f"Case: {case['title']}\nOrder date: {newest['date']}\n\nOrder text:\n{text}",
                       DIRECTIONS_SCHEMA)
            for i, d in enumerate(dres.get("directions", [])):
                did = f"{cid}-{newest['date'].replace('-','')}-{i}"
                if did in existing_dir_ids:
                    continue
                # Backstop against recited prior directions the prompt failed to skip:
                # if this restates a direction already on the ledger for this case,
                # the original entry (with its original clock) stands.
                dup = near_duplicate(d["directive"], cid, dirdata["directions"])
                if dup:
                    log.setdefault("skipped_recitals", []).append(
                        {"case": cid, "directive": d["directive"][:80], "duplicate_of": dup})
                    continue
                due = compute_due(newest["date"], d["granted"])
                entry = {
                    "id": did, "case_id": cid, "order_date": newest["date"],
                    "order_tid": newest["tid"], "directive": d["directive"],
                    "authority": d["authority"], "granted": d["granted"],
                    "due": due, "theme": d["theme"],
                }
                if due is None:
                    entry["status"] = "ongoing"
                dirdata["directions"].append(entry)
                existing_dir_ids.add(did)
                dir_changed = True
                log.setdefault("new_directions", []).append({"case": cid, "directive": d["directive"][:80], "due": due})
          except Exception as e:
            log["errors"].append(f"gist/directions case={cid} order={newest['date']}: {e}")

    if dir_changed:
        DIR_PATH.write_text(json.dumps(dirdata, indent=2, ensure_ascii=False))
        changed = True

    if changed:
        CURATION_PATH.write_text(json.dumps(curation, indent=2, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_registry.py")], check=True)
        # build_registry resets new_this_refresh — restore it (grown cases + newly added)
        registry = json.loads((ROOT / "data" / "cases.json").read_text())
        registry["new_this_refresh"] = sorted(set(grew) | set(new_case_ids))
        registry["meta"]["built"] = date.today().isoformat()
        (ROOT / "data" / "cases.json").write_text(json.dumps(registry, indent=1, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_dashboard.py")], check=True)

    log["doc_fetches"] = DOC_FETCHES["n"]
    log["approx_doc_cost_inr"] = round(DOC_FETCHES["n"] * 0.2, 1)
    (ROOT / "data" / "curation_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
    print(json.dumps(log, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
