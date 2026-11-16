"""A failed curation run must not lose work.

Before the pending queue, auto_curate read candidates and grown cases only from
the CURRENT refresh_report. When the LLM was unavailable (3 and 10 Nov 2026:
401 on the subscription token) the next refresh overwrote the report, and that
week's candidates and order gists were never retried.

Run: python3 -m unittest discover -s tests -v
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import auto_curate as ac  # noqa: E402


def write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def read(p: Path):
    return json.loads(p.read_text())


class Fixture:
    """A throwaway repo tree with one tracked case that has two orders."""

    def __init__(self, tmp: str):
        self.root = Path(tmp)
        write(self.root / "data" / "cases.json", {
            "meta": {"built": ""},
            "cases": [{
                "id": "case-a", "title": "Case A", "case_number": "W.P.(C) 1/2026",
                "order_count": 2, "latest_order": "2026-11-02",
                "orders": [
                    {"date": "2026-10-01", "tid": 101, "gist": "", "significance": "routine"},
                    {"date": "2026-11-02", "tid": 102, "gist": "", "significance": "routine"},
                ],
            }],
            "new_this_refresh": [],
        })
        write(self.root / "pipeline" / "curation.json", {
            "_comment": "test",
            "tracked_cases": [{
                "id": "case-a", "match": ["case a"], "title": "Case A",
                "latest_development": "ORIGINAL", "order_notes": {},
                "next_listing": "1 October 2026 (per order of 2026-09-01)",
            }],
            "notable_judgments": [], "borderline_excluded": [],
        })
        write(self.root / "pipeline" / "directions.json", {"_comment": "test", "directions": []})

    def report(self, day, candidates=(), grew=None):
        grew = grew or {}
        write(self.root / "data" / "refresh_report.json", {
            "refresh_date": day,
            "cases_with_new_orders": list(grew),
            "new_order_counts": dict(grew),
            "new_unassigned_candidates": [
                {"tid": t, "date": "2026-10-20", "title": f"Candidate {t} vs State", "headline": ""}
                for t in candidates],
        })

    @property
    def log(self):
        return read(self.root / "data" / "curation_log.json")

    @property
    def queue(self):
        p = self.root / "data" / "curation_pending.json"
        return read(p) if p.exists() else {"candidates": [], "orders": []}

    @property
    def spec(self):
        return read(self.root / "pipeline" / "curation.json")["tracked_cases"][0]


class Calls:
    """Stands in for auto_curate.ask. mode: 'ok', 'down', 'error', or an int N
    meaning the subscription dies after N successful calls."""

    def __init__(self, mode="ok"):
        self.mode = mode
        self.seen = []

    def __call__(self, system, user, schema):
        if self.mode == "down" or (isinstance(self.mode, int) and len(self.seen) >= self.mode):
            ac._down("credential refused - refresh CLAUDE_CODE_OAUTH_TOKEN: 401")
        if self.mode == "error":
            raise RuntimeError("no JSON object in reply")
        self.seen.append(user.splitlines()[0])
        if schema is ac.CLASSIFY_SCHEMA:
            return {"action": "ignore", "reason": "not road safety", "title": "t",
                    "case_number": "", "case_type": "", "status": "unknown", "filed_year": 2026,
                    "themes": [], "why_it_matters": "", "gist": "", "match_pattern": ""}
        if schema is ac.GIST_SCHEMA:
            date = user.split("Order date: ")[1][:10]
            return {"gist": f"gist of {date}", "significance": "major",
                    "latest_development": f"DEV {date}", "next_listing": ""}
        return {"directions": []}


class PendingQueueTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def run_curation(self, mode="ok"):
        calls = Calls(mode)
        ac.LLM_DOWN["reason"] = None
        ac.DOC_FETCHES["n"] = 0
        with mock.patch.object(ac, "ROOT", self.fx.root), \
             mock.patch.object(ac, "CURATION_PATH", self.fx.root / "pipeline" / "curation.json"), \
             mock.patch.object(ac, "doc_text", lambda tid, limit=24000: f"text of {tid}"), \
             mock.patch.object(ac, "ask", calls), \
             mock.patch.object(ac.subprocess, "run", lambda *a, **k: None), \
             mock.patch("builtins.print"):
            ac.main()
        return calls

    def test_work_from_a_failed_run_is_done_by_the_next_run(self):
        """The 3 Nov -> 10 Nov scenario."""
        self.fx.report("2026-11-03", candidates=[901, 902], grew={"case-a": 1})
        self.run_curation("down")
        self.assertIn("llm_unavailable", self.fx.log)
        self.assertEqual([c["tid"] for c in self.fx.queue["candidates"]], [901, 902])
        self.assertEqual([o["tid"] for o in self.fx.queue["orders"]], [102])

        # next week: the refresh finds nothing new and overwrites the report
        self.fx.report("2026-11-10")
        self.run_curation("ok")
        self.assertEqual([c["tid"] for c in self.fx.log["classified"]], [901, 902])
        self.assertEqual([(g["case"], g["date"]) for g in self.fx.log["gists"]], [("case-a", "2026-11-02")])
        self.assertEqual(self.fx.spec["order_notes"]["2026-11-02"]["gist"], "gist of 2026-11-02")
        self.assertEqual(self.fx.spec["latest_development"], "DEV 2026-11-02")
        self.assertEqual(self.fx.queue["candidates"], [])
        self.assertEqual(self.fx.queue["orders"], [])
        self.assertNotIn("llm_unavailable", self.fx.log)

    def test_only_unfinished_items_stay_queued_when_the_llm_dies_midway(self):
        self.fx.report("2026-11-03", candidates=[901, 902, 903])
        self.run_curation(1)
        self.assertEqual([c["tid"] for c in self.fx.log["classified"]], [901])
        self.assertEqual([c["tid"] for c in self.fx.queue["candidates"]], [902, 903])

    def test_rerunning_on_the_same_report_does_not_redo_finished_work(self):
        self.fx.report("2026-11-03", candidates=[901], grew={"case-a": 1})
        self.run_curation("ok")
        again = self.run_curation("ok")
        self.assertEqual(again.seen, [])

    def test_a_late_gist_for_an_older_order_does_not_overwrite_newer_curation(self):
        """Order 101 is retried after 102 was already curated: its gist is
        recorded, but the case's headline state stays with the newer order."""
        write(self.fx.root / "data" / "curation_pending.json", {
            "candidates": [],
            "orders": [{"case": "case-a", "tid": 101, "date": "2026-10-01", "queued": "2026-10-06"}]})
        self.fx.report("2026-11-10")
        self.run_curation("ok")
        self.assertEqual(self.fx.spec["order_notes"]["2026-10-01"]["gist"], "gist of 2026-10-01")
        self.assertEqual(self.fx.spec["latest_development"], "ORIGINAL")
        self.assertEqual(self.fx.spec["next_listing"], "1 October 2026 (per order of 2026-09-01)")
        self.assertEqual(self.fx.queue["orders"], [])

    def test_an_item_that_keeps_failing_is_dropped_loudly_not_retried_forever(self):
        self.fx.report("2026-11-03", candidates=[901])
        for day in ("2026-11-03", "2026-11-10"):
            self.fx.report(day, candidates=[901] if day == "2026-11-03" else [])
            self.run_curation("error")
            self.assertEqual([c["tid"] for c in self.fx.queue["candidates"]], [901])
            self.assertNotIn("gave_up", self.fx.log)
        self.fx.report("2026-11-17")
        self.run_curation("error")
        self.assertEqual(self.fx.queue["candidates"], [])
        self.assertEqual(self.fx.log["gave_up"][0]["tid"], 901)

    def test_an_llm_outage_does_not_count_against_an_item(self):
        self.fx.report("2026-11-03", candidates=[901])
        for day in ("2026-11-03", "2026-11-10", "2026-11-17", "2026-11-24"):
            self.fx.report(day, candidates=[901] if day == "2026-11-03" else [])
            self.run_curation("down")
        self.assertEqual([c["tid"] for c in self.fx.queue["candidates"]], [901])
        self.assertEqual(self.fx.queue["candidates"][0].get("attempts", 0), 0)


if __name__ == "__main__":
    unittest.main()
