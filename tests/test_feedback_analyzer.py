"""Tests for privacy-conscious feedback summaries."""

import tempfile
import unittest
from pathlib import Path

from krisona_ai.feedback_analyzer import summarize_feedback
from krisona_ai.mission_store import MissionStore


def make_record(mission_id: str, domain: str) -> dict:
    return {
        "mission": {
            "mission_id": mission_id,
            "domain": domain,
            "status": "identified",
        }
    }


class FeedbackAnalyzerTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = MissionStore(
            Path(self.temp.name) / "private" / "test.sqlite3"
        )

    def test_empty_store_reports_no_feedback(self):
        result = summarize_feedback(self.store)
        self.assertEqual(result["status"], "no_feedback")
        self.assertEqual(result["feedback_count"], 0)
        self.assertIsNone(result["average_rating"])

    def test_calculates_overall_feedback_metrics(self):
        self.store.save_mission(make_record("career-1", "career"))
        self.store.save_mission(make_record("education-1", "education"))

        self.store.record_feedback(
            "career-1", {"rating": 5, "helpful": True}
        )
        self.store.record_feedback(
            "career-1", {"rating": 3, "helpful": False}
        )
        self.store.record_feedback(
            "education-1", {"rating": 4, "helpful": True}
        )

        result = summarize_feedback(self.store)

        self.assertEqual(result["status"], "summary_ready")
        self.assertEqual(result["mission_count"], 2)
        self.assertEqual(result["feedback_count"], 3)
        self.assertEqual(result["average_rating"], 4.0)
        self.assertEqual(result["helpfulness_count"], 3)
        self.assertEqual(result["helpful_count"], 2)
        self.assertEqual(result["helpful_rate_percent"], 66.7)

    def test_metrics_are_grouped_by_domain(self):
        self.store.save_mission(make_record("career-1", "career"))
        self.store.save_mission(make_record("education-1", "education"))
        self.store.record_feedback(
            "career-1", {"rating": 5, "helpful": True}
        )
        self.store.record_feedback(
            "education-1", {"rating": 2, "helpful": False}
        )

        result = summarize_feedback(self.store)

        self.assertEqual(
            result["domains"]["career"]["average_rating"], 5.0
        )
        self.assertEqual(
            result["domains"]["education"]["average_rating"], 2.0
        )

    def test_missing_rating_is_not_treated_as_zero(self):
        self.store.save_mission(make_record("career-1", "career"))
        self.store.record_feedback(
            "career-1", {"helpful": True}
        )

        result = summarize_feedback(self.store)

        self.assertEqual(result["feedback_count"], 1)
        self.assertEqual(result["rating_count"], 0)
        self.assertIsNone(result["average_rating"])

    def test_comments_are_not_exposed_in_summary(self):
        self.store.save_mission(make_record("career-1", "career"))
        self.store.record_feedback(
            "career-1",
            {
                "rating": 4,
                "comments": "PRIVATE_COMMENT_SHOULD_NOT_APPEAR",
            },
        )

        result = summarize_feedback(self.store)

        self.assertNotIn(
            "PRIVATE_COMMENT_SHOULD_NOT_APPEAR", repr(result)
        )

    def test_summary_does_not_change_stored_feedback(self):
        self.store.save_mission(make_record("career-1", "career"))
        self.store.record_feedback(
            "career-1", {"rating": 4, "helpful": True}
        )

        before = self.store.list_feedback("career-1")
        summarize_feedback(self.store)
        after = self.store.list_feedback("career-1")

        self.assertEqual(before, after)

    def test_invalid_limit_is_rejected(self):
        for limit in (True, 0, 101, "10"):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    summarize_feedback(self.store, limit=limit)

    def test_wrong_store_type_is_rejected(self):
        with self.assertRaises(TypeError):
            summarize_feedback("not a store")


if __name__ == "__main__":
    unittest.main()
