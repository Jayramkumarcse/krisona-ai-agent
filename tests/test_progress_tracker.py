"""Tests for daily progress check-ins and weekly review."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from krisona_ai.mission_store import MissionStore
from krisona_ai.progress_tracker import (
    create_weekly_review,
    summarize_progress,
)


class ProgressTrackerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = MissionStore(Path(temp.name) / "test.sqlite3")
        self.mission_id = "mission-progress-test"
        self.store.save_mission({
            "mission_id": self.mission_id,
            "created_at": "2026-01-01T00:00:00+00:00",
            "situation": "Improve spoken English",
            "workflow_result": {
                "status": "advice_ready",
                "mission": {
                    "mission_id": self.mission_id,
                    "goal": "improve spoken English",
                    "domain": "daily_life",
                },
            },
        })

    def test_checkins_are_summarized(self):
        today = date(2026, 10, 21)
        self.store.record_progress_checkin(
            self.mission_id, minutes=15, activity="Voice note",
            completed=True, self_rating=4, checkin_date=today.isoformat(),
        )
        self.store.record_progress_checkin(
            self.mission_id, minutes=10, activity="Introduction practice",
            completed=False, self_rating=2,
            checkin_date=(today - timedelta(days=1)).isoformat(),
        )

        result = summarize_progress(self.store, self.mission_id, today=today)
        self.assertEqual(result["overall"]["checkins"], 2)
        self.assertEqual(result["overall"]["practice_minutes"], 25)
        self.assertEqual(result["overall"]["completed_sessions"], 1)
        self.assertEqual(result["overall"]["average_self_rating"], 3.0)
        self.assertEqual(result["last_7_days"]["active_days"], 2)

    def test_empty_progress_is_not_fabricated(self):
        result = summarize_progress(
            self.store, self.mission_id, today=date(2026, 10, 21)
        )
        self.assertEqual(result["status"], "no_checkins")
        self.assertEqual(result["overall"]["practice_minutes"], 0)
        self.assertIsNone(result["overall"]["completion_rate_percent"])

    def test_weekly_review_uses_recorded_data(self):
        today = date(2026, 10, 21)
        self.store.record_progress_checkin(
            self.mission_id, minutes=5, activity="Short practice",
            completed=False, self_rating=2, checkin_date=today.isoformat(),
        )
        review = create_weekly_review(self.store, self.mission_id, today=today)
        self.assertEqual(review["status"], "weekly_review_ready")
        self.assertIn("smaller", review["recommendation"])

    def test_invalid_minutes_are_rejected(self):
        for minutes in (-1, 1441, True, 1.5):
            with self.subTest(minutes=minutes):
                with self.assertRaises(ValueError):
                    self.store.record_progress_checkin(
                        self.mission_id, minutes=minutes,
                        activity="Practice", completed=True,
                    )

    def test_invalid_rating_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "self_rating"):
            self.store.record_progress_checkin(
                self.mission_id, minutes=10, activity="Practice",
                completed=True, self_rating=6,
            )

    def test_unknown_mission_is_rejected(self):
        with self.assertRaises(KeyError):
            self.store.record_progress_checkin(
                "unknown-mission", minutes=10,
                activity="Practice", completed=True,
            )


if __name__ == "__main__":
    unittest.main()
