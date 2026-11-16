"""New cases and judgments only get chip topics from the fixed lists.

The dashboard's filter chips are built from `topics` (cases) and `topic`
(precedents). Free-form tags grew to 30 for 20 cases; these fields must not.

Run: python3 -m unittest discover -s tests -v
"""

import unittest
from unittest import mock

import auto_curate as ac
from test_pending_queue import Fixture, read

import tempfile


def reply(action, **over):
    base = {"action": action, "reason": "r", "title": "Road Users v. Union of India",
            "case_number": "W.P.(C) 9/2026", "case_type": "PIL", "status": "pending",
            "filed_year": 2026, "themes": ["a brand new free tag"], "topics": [],
            "precedent_topic": "", "why_it_matters": "w", "gist": "g",
            "match_pattern": "road users"}
    base.update(over)
    return base


class TopicsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.fx = Fixture(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def classify(self, result):
        self.fx.report("2026-11-17", candidates=[901])
        ac.LLM_DOWN["reason"] = None
        ac.DOC_FETCHES["n"] = 0
        with mock.patch.object(ac, "ROOT", self.fx.root), \
             mock.patch.object(ac, "CURATION_PATH", self.fx.root / "pipeline" / "curation.json"), \
             mock.patch.object(ac, "doc_text", lambda tid, limit=24000: "text"), \
             mock.patch.object(ac, "ask", lambda system, user, schema: result), \
             mock.patch.object(ac.subprocess, "run", lambda *a, **k: None), \
             mock.patch("builtins.print"):
            ac.main()
        return read(self.fx.root / "pipeline" / "curation.json")

    def test_schema_offers_only_the_fixed_lists(self):
        props = ac.CLASSIFY_SCHEMA["properties"]
        self.assertEqual(props["topics"]["items"]["enum"], ac.CASE_TOPICS)
        self.assertEqual(props["precedent_topic"]["enum"], ac.PRECEDENT_TOPICS + [""])
        self.assertIn("topics", ac.CLASSIFY_SCHEMA["required"])
        self.assertIn("precedent_topic", ac.CLASSIFY_SCHEMA["required"])

    def test_a_tracked_case_keeps_only_listed_topics(self):
        cur = self.classify(reply("track", topics=["enforcement", "something invented", "highways"]))
        new = cur["tracked_cases"][-1]
        self.assertEqual(new["topics"], ["enforcement", "highways"])
        self.assertEqual(new["themes"], ["a brand new free tag"])   # free tags are untouched

    def test_a_notable_judgment_gets_its_topic(self):
        cur = self.classify(reply("notable", precedent_topic="Criminal sentencing"))
        self.assertEqual(cur["notable_judgments"][-1]["topic"], "Criminal sentencing")

    def test_an_unlisted_precedent_topic_is_left_off(self):
        cur = self.classify(reply("notable", precedent_topic="Misc"))
        self.assertNotIn("topic", cur["notable_judgments"][-1])

    def test_a_reply_without_the_new_fields_still_works(self):
        r = reply("track"); del r["topics"]; del r["precedent_topic"]
        cur = self.classify(r)
        self.assertEqual(cur["tracked_cases"][-1]["topics"], [])


if __name__ == "__main__":
    unittest.main()
