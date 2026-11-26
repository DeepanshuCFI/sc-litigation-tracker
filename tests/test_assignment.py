"""A document that already belongs to a tracked case must never become a new case.

18 Nov 2026: the Phalodi judgment (tid 141342595) and its daily-order copy
(tid 165603562) shared a date. The registry kept the daily order, refresh.py
looked only at timeline tids, called the judgment "unassigned", and the
classifier filed it as a second Phalodi case on the live site.

Run: python3 -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
import auto_curate as ac  # noqa: E402
import build_registry as br  # noqa: E402

CURATION = {"tracked_cases": [
    {"id": "phalodi-smwpc-9-2025", "match": ["in re: phalodi accident"]},
    {"id": "old-case", "match": ["some petitioner"], "date_min": "2010-01-01", "date_max": "2015-12-31"},
]}
TITLE = "In Re: <b>Phalodi</b> Accident vs National Highways Authority Of India on 18 November, 2026"


class OwningCase(unittest.TestCase):
    def test_judgment_twin_belongs_to_the_tracked_case(self):
        self.assertEqual(ac.owning_case(CURATION, TITLE, "2026-11-18"), "phalodi-smwpc-9-2025")

    def test_unrelated_document_belongs_to_none(self):
        self.assertEqual(ac.owning_case(CURATION, "Sukumarbai vs United India Insurance Company Ltd "
                                                  "on 25 November, 2026", "2026-11-25"), "")

    def test_date_window_is_respected(self):
        self.assertEqual(ac.owning_case(CURATION, "Some Petitioner vs Union of India", "2012-05-01"), "old-case")
        self.assertEqual(ac.owning_case(CURATION, "Some Petitioner vs Union of India", "2026-05-01"), "")


class CollapseByDate(unittest.TestCase):
    def test_judgment_wins_over_daily_order_on_the_same_date(self):
        hits = [
            {"tid": 165603562, "publishdate": "2026-11-18", "docsource": "Supreme Court - Daily Orders"},
            {"tid": 141342595, "publishdate": "2026-11-18", "docsource": "Supreme Court of India"},
            {"tid": 160899034, "publishdate": "2026-10-13", "docsource": "Supreme Court - Daily Orders"},
        ]
        by_date = br.collapse_by_date(hits)
        self.assertEqual(by_date["2026-11-18"]["tid"], 141342595)
        self.assertEqual(by_date["2026-10-13"]["tid"], 160899034)
        self.assertEqual(br.collapse_by_date(list(reversed(hits)))["2026-11-18"]["tid"], 141342595)


if __name__ == "__main__":
    unittest.main()
