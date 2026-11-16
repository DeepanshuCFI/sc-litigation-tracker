#!/usr/bin/env python3
"""LLM curation layer for the weekly refresh (runs after refresh.py).

Reads data/refresh_report.json. For each new unassigned candidate, fetches the
document text from Indian Kanoon and asks Claude to classify it per the
inclusion rule in pipeline/curation.json. For each tracked case with new
orders, fetches the newest order and asks Claude for a gist + significance +
updated latest_development. Applies changes to curation.json, rebuilds the
registry and dashboard, and writes data/curation_log.json.

Work is driven from a persistent queue, data/curation_pending.json, not from
the report directly. Each run first copies the report's candidates and new
orders into the queue, then works the queue, removing an item only once it has
been curated. refresh.py overwrites the report every week, so without the queue
a run that could not reach the LLM lost that week's work for good (3 and 10 Nov
2026: five candidates never classified, two orders never gisted).

Inference runs on Deepanshu's Claude subscription through the `claude` CLI
(`claude -p`), never the metered API: his standing rule since 16 Oct 2026. In
CI the CLI authenticates with CLAUDE_CODE_OAUTH_TOKEN (from `claude setup-token`);
on a Mac it uses the interactive login. ANTHROPIC_API_KEY is stripped from the
CLI's environment so nothing can silently fall back to billing.

Degrades gracefully: a failed call logs the error and the run exits 0, so the
mechanical refresh (new orders with links) still gets committed. A dead token or
an exhausted subscription limit stops all further calls and sets
`llm_unavailable` in data/curation_log.json; the workflow fails the job on that
flag AFTER the commit, so the failure notification fires without losing data.

Env: CLAUDE_CODE_OAUTH_TOKEN (CI), IK_API_TOKEN.
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ik_client

ROOT = Path(__file__).resolve().parent.parent
CURATION_PATH = ROOT / "pipeline" / "curation.json"
MODEL = "claude-opus-5"
CLI_TIMEOUT_S = 300

# Fixed lists behind the dashboard's filter chips. `themes` stays free-form (the
# fine tags printed on each case card and matched by search); `topics` and
# `precedent_topic` must come from these lists so the chip rows stop growing by
# one tag per new case (30 themes for 20 cases by Nov 2026).
CASE_TOPICS = ["victim compensation", "MACT process", "insurance", "post-crash care", "good samaritan", "highways", "road engineering", "pedestrian safety", "enforcement", "licensing and vehicles", "institutions"]
PRECEDENT_TOPICS = ["Compensation method", "Insurer liability and licence defences", "Claims procedure and jurisdiction", "Criminal sentencing", "Regulation and prevention"]

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
        "topics": {"type": "array", "items": {"type": "string", "enum": CASE_TOPICS}},
        "precedent_topic": {"type": "string", "enum": PRECEDENT_TOPICS + [""]},
        "why_it_matters": {"type": "string"},
        "gist": {"type": "string"},
        "match_pattern": {"type": "string"},
    },
    "required": ["action", "reason", "title", "case_number", "case_type", "status",
                 "filed_year", "themes", "topics", "precedent_topic", "why_it_matters", "gist",
                 "match_pattern"],
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


# A refused credential or an exhausted subscription limit is not a per-document
# problem: every later call would fail the same way. Matched only against the
# CLI's own error text, never against order text.
_AUTH_FAIL = re.compile(
    r"failed to authenticate|\b401\b|\b403\b|invalid (api key|x-api-key)|"
    r"oauth.{0,40}(invalid|expired|revoked)|authentication_error|not logged in", re.I)
_LIMIT = re.compile(r"usage limit|weekly limit|hit your .{0,20}limit|rate.?limit", re.I)
LLM_DOWN = {"reason": None}


class LLMUnavailable(RuntimeError):
    pass


def _cli_env() -> dict:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)   # never let the CLI bill the API instead
    env.pop("ANTHROPIC_AUTH_TOKEN", None)
    return env


def _down(reason: str):
    LLM_DOWN["reason"] = reason
    raise LLMUnavailable(reason)


def ask(system: str, user: str, schema: dict) -> dict:
    """One structured call on the subscription via `claude -p`. The CLI has no
    schema-enforced output mode, so the schema goes in the prompt and the reply is
    parsed and checked for the required keys (the infra-defect pipeline's pattern)."""
    if LLM_DOWN["reason"]:
        raise LLMUnavailable(LLM_DOWN["reason"])
    binary = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if not binary:
        _down("claude CLI not found - install @anthropic-ai/claude-code")
    prompt = (f"{system}\n\nReturn a SINGLE JSON object matching this JSON schema exactly. "
              f"No prose, no markdown fence, no commentary - the object only.\n"
              f"SCHEMA:\n{json.dumps(schema, ensure_ascii=False)}\n\n{user}")
    try:
        # prompt on stdin: order text runs to ~24k chars
        p = subprocess.run(
            [binary, "-p", "--model", MODEL, "--output-format", "json", "--max-turns", "1"],
            input=prompt, capture_output=True, text=True, timeout=CLI_TIMEOUT_S,
            env=_cli_env())
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"claude CLI timed out after {CLI_TIMEOUT_S}s")
    err = (p.stderr or "")[:400]
    try:
        envelope = json.loads(p.stdout)
    except json.JSONDecodeError:
        if _AUTH_FAIL.search(err) or _LIMIT.search(err):
            _down(f"claude CLI refused: {err}")
        raise RuntimeError(f"claude CLI exited {p.returncode} with no JSON envelope: {err or p.stdout[:200]}")
    result = str(envelope.get("result") or "")
    if envelope.get("is_error"):
        if _LIMIT.search(result) or _LIMIT.search(err):
            _down(f"subscription usage limit reached (token is fine, do NOT refresh it): {result[:300]}")
        if _AUTH_FAIL.search(result) or _AUTH_FAIL.search(err):
            _down(f"credential refused - refresh CLAUDE_CODE_OAUTH_TOKEN: {result[:300]}")
        raise RuntimeError(f"claude CLI error: {result[:300]}")
    m = re.search(r"```(?:json)?\s*(.*?)```", result, re.S)
    body = m.group(1) if m else result
    start, end = body.find("{"), body.rfind("}")
    if start == -1 or end <= start:
        raise RuntimeError(f"no JSON object in reply: {result[:200]}")
    out = json.loads(body[start:end + 1])
    missing = [k for k in schema.get("required", []) if k not in out]
    if missing:
        raise RuntimeError(f"reply missing required keys {missing}")
    return out


def owning_case(curation: dict, title: str, doc_date: str) -> str:
    """id of the tracked case whose title pattern (and date window) already
    covers this document, or '' when it belongs to none."""
    nt = norm_title(title)
    for spec in curation.get("tracked_cases", []):
        if (any(m and m in nt for m in spec.get("match", []))
                and spec.get("date_min", "0000") <= (doc_date or "?") <= spec.get("date_max", "9999")):
            return spec["id"]
    return ""


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


# An item that fails this many runs for a reason of its own (unreadable document,
# malformed reply) leaves the queue and is reported, so one bad document cannot be
# re-fetched from Indian Kanoon every week forever. LLM outages never count.
MAX_ATTEMPTS = 3


def load_pending(path: Path) -> dict:
    pending = json.loads(path.read_text()) if path.exists() else {}
    pending.setdefault("candidates", [])
    pending.setdefault("orders", [])
    return pending


def enqueue_report(pending: dict, report: dict, by_id: dict) -> None:
    """Copy this refresh's candidates and new orders into the queue, once.

    The signature stops a second auto_curate run on the same report (a manual
    re-run, a local test) from re-queueing work that has already been done."""
    candidates = report.get("new_unassigned_candidates", [])
    counts = report.get("new_order_counts", {})
    grew = report.get("cases_with_new_orders", [])
    if not candidates and not grew:
        return
    sig = json.dumps([report.get("refresh_date"), sorted(str(c["tid"]) for c in candidates),
                      sorted((cid, counts.get(cid, 1)) for cid in grew)])
    if pending.get("ingested_report") == sig:
        return
    today = date.today().isoformat()
    have = {str(c["tid"]) for c in pending["candidates"]}
    for c in candidates:
        if str(c["tid"]) not in have:
            pending["candidates"].append({"tid": c["tid"], "date": c["date"], "title": c["title"],
                                          "queued": today})
            have.add(str(c["tid"]))
    have = {str(o["tid"]) for o in pending["orders"]}
    for cid in grew:
        case = by_id.get(cid)
        if not case or not case.get("orders"):
            continue
        # every order added this refresh, not just the newest: after court
        # vacations a case routinely gains 2+ orders in one window
        for o in case["orders"][-max(1, counts.get(cid, 1)):]:
            if str(o["tid"]) not in have:
                pending["orders"].append({"case": cid, "tid": o["tid"], "date": o["date"],
                                          "queued": today})
                have.add(str(o["tid"]))
    pending["ingested_report"] = sig


def note_failure(item: dict, queue: list, log: dict, kind: str, err: Exception) -> None:
    """Count a failure that was the item's own, and give up after MAX_ATTEMPTS."""
    item["attempts"] = item.get("attempts", 0) + 1
    item["last_error"] = str(err)[:200]
    if item["attempts"] >= MAX_ATTEMPTS:
        queue.remove(item)
        log.setdefault("gave_up", []).append(
            {"kind": kind, **{k: item[k] for k in ("case", "tid", "date", "title") if k in item},
             "attempts": item["attempts"], "last_error": item["last_error"]})


def main() -> None:
    report_path = ROOT / "data" / "refresh_report.json"
    if not report_path.exists():
        print("no refresh report — nothing to curate")
        return
    report = json.loads(report_path.read_text())
    grew = report.get("cases_with_new_orders", [])

    registry = json.loads((ROOT / "data" / "cases.json").read_text())
    by_id = {cs["id"]: cs for cs in registry["cases"]}

    pending_path = ROOT / "data" / "curation_pending.json"
    pending = load_pending(pending_path)
    pending_before = json.dumps(pending, sort_keys=True)
    carried = {"candidates": len(pending["candidates"]), "orders": len(pending["orders"])}
    enqueue_report(pending, report, by_id)
    if not pending["candidates"] and not pending["orders"]:
        print("nothing new and nothing pending — no curation needed")
        return

    log = {"date": date.today().isoformat(), "classified": [], "gists": [], "errors": []}
    if carried["candidates"] or carried["orders"]:
        log["carried_over"] = carried   # work left by an earlier run that could not finish
    curation = json.loads(CURATION_PATH.read_text())
    changed = False
    new_case_ids = []

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
        "be a lowercase substring of the case title (petitioner name) usable to match related orders. "
        "topics: one to three entries from the fixed list in the schema, for a case you would 'track' "
        "(empty list otherwise). precedent_topic: exactly one entry from the fixed list for a 'notable' "
        "judgment, describing the rule it sets (empty string otherwise). themes may be free text."
    )

    # 1. classify new unassigned candidates
    for c in list(pending["candidates"]):
        owner = owning_case(curation, c.get("title", ""), c.get("date", ""))
        if owner:
            # already part of a tracked case (e.g. the judgment twin of a daily
            # order): classifying it could only create a duplicate case
            log.setdefault("already_tracked", []).append(
                {"tid": c["tid"], "date": c["date"], "title": c["title"], "case": owner})
            pending["candidates"].remove(c)
            continue
        if LLM_DOWN["reason"]:
            break  # don't pay IK for documents nobody can classify
        try:
            text = doc_text(c["tid"])
            result = ask(classify_system,
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
                    # only values from the fixed list reach the chips; a reply that
                    # ignores the list simply leaves the case without a topic
                    "topics": [t for t in result.get("topics", []) if t in CASE_TOPICS][:3],
                    "why_it_matters": result["why_it_matters"],
                    "latest_development": f"{c['date']}: {result['gist']}" if result["gist"] else "",
                    "order_notes": {c["date"]: {"gist": result["gist"], "significance": "major"}} if result["gist"] else {},
                })
                new_case_ids.append(cid)
                changed = True
            elif result["action"] == "notable":
                nj = {"tid": c["tid"], "date": c["date"], "title": result["title"],
                      "gist": result["gist"]}
                if result.get("precedent_topic") in PRECEDENT_TOPICS:
                    nj["topic"] = result["precedent_topic"]
                curation["notable_judgments"].append(nj)
                changed = True
            elif result["action"] == "borderline":
                curation["borderline_excluded"].append({"why": result["reason"], "cases": [result["title"]]})
                changed = True
            pending["candidates"].remove(c)   # classified, whatever the verdict
        except LLMUnavailable as e:
            log["errors"].append(f"classify tid={c.get('tid')}: {e}")   # stays queued
        except Exception as e:
            log["errors"].append(f"classify tid={c.get('tid')}: {e}")
            note_failure(c, pending["candidates"], log, "candidate", e)

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

    # Chronological order, so the newest order wins latest_development.
    pending["orders"].sort(key=lambda o: (o["date"], str(o["tid"])))
    gisted_cases = set()
    for item in list(pending["orders"]):
          if LLM_DOWN["reason"]:
              break
          cid = item["case"]
          case = by_id.get(cid)
          spec = next((s for s in curation["tracked_cases"] if s["id"] == cid), None)
          newest = next((o for o in (case or {}).get("orders", [])
                         if str(o["tid"]) == str(item["tid"])), None)
          if not spec or not newest:
              # the case was removed or re-matched since this order was queued
              pending["orders"].remove(item)
              log.setdefault("dropped", []).append(
                  {"case": cid, "tid": item["tid"], "date": item["date"],
                   "why": "case or order no longer in the registry"})
              continue
          # A retried order can be older than one already curated. Its gist and
          # directions still belong on the record, but it must not drag the case's
          # headline state (latest development, next listing) back in time.
          queued_tids = {str(o["tid"]) for o in pending["orders"]}
          superseded = any(o["date"] > newest["date"] and str(o["tid"]) not in queued_tids
                           for o in case["orders"])
          try:
            text = doc_text(newest["tid"])
            result = ask(gist_system,
                         f"Case: {case['title']} ({case['case_number']})\nOrder date: {newest['date']}\n\nOrder text:\n{text}",
                         GIST_SCHEMA)
            log["gists"].append({"case": cid, "date": newest["date"], **result})
            if result["significance"] == "major" and result["gist"]:
                spec.setdefault("order_notes", {})[newest["date"]] = {
                    "gist": result["gist"], "significance": "major"}
            if not superseded:
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
            dres = ask(dir_system,
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
            pending["orders"].remove(item)
            gisted_cases.add(cid)
          except LLMUnavailable as e:
            log["errors"].append(f"gist/directions case={cid} order={newest['date']}: {e}")   # stays queued
          except Exception as e:
            log["errors"].append(f"gist/directions case={cid} order={newest['date']}: {e}")
            note_failure(item, pending["orders"], log, "order", e)

    if dir_changed:
        DIR_PATH.write_text(json.dumps(dirdata, indent=2, ensure_ascii=False))
        changed = True

    if changed:
        CURATION_PATH.write_text(json.dumps(curation, indent=2, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_registry.py")], check=True)
        # build_registry resets new_this_refresh — restore it (grown cases + newly added)
        registry = json.loads((ROOT / "data" / "cases.json").read_text())
        registry["new_this_refresh"] = sorted(set(grew) | set(new_case_ids) | gisted_cases)
        registry["meta"]["built"] = date.today().isoformat()
        (ROOT / "data" / "cases.json").write_text(json.dumps(registry, indent=1, ensure_ascii=False))
        subprocess.run([sys.executable, str(ROOT / "pipeline" / "build_dashboard.py")], check=True)

    if LLM_DOWN["reason"]:
        log["llm_unavailable"] = LLM_DOWN["reason"]
        print(f"LLM curation stopped early: {LLM_DOWN['reason']}", file=sys.stderr)
    if pending["candidates"] or pending["orders"]:
        log["pending"] = {"candidates": len(pending["candidates"]), "orders": len(pending["orders"])}
    if json.dumps(pending, sort_keys=True) != pending_before:
        pending_path.write_text(json.dumps(pending, indent=1, ensure_ascii=False))
    log["doc_fetches"] = DOC_FETCHES["n"]
    log["approx_doc_cost_inr"] = round(DOC_FETCHES["n"] * 0.2, 1)
    (ROOT / "data" / "curation_log.json").write_text(json.dumps(log, indent=1, ensure_ascii=False))
    print(json.dumps(log, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
