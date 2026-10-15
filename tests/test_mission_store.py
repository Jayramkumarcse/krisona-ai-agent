"""Tests for local mission persistence, task progress, and feedback."""

import os
import stat
import tempfile
import unittest
from pathlib import Path

from krisona_ai.mission_store import MissionStore


def sample_record(mission_id="mission-001"):
    return {
        "status": "plan_ready",
        "mission": {
            "mission_id": mission_id,
            "domain": "career",
            "status": "identified",
        },
        "plan": {
            "status": "planned",
            "days": [{
                "date": "2026-10-16",
                "tasks": [{
                    "id": "resume",
                    "title": "Prepare resume",
                    "status": "pending",
                    "duration_minutes": 30,
                }],
            }],
        },
    }


class MissionStoreTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        db_path = Path(self.temp.name) / "private" / "missions.sqlite3"
        self.store = MissionStore(db_path)
        self.record = sample_record()
        self.store.save_mission(self.record)

    def test_save_and_load_mission(self):
        loaded = self.store.get_mission("mission-001")
        self.assertEqual(loaded, self.record)

    def test_duplicate_mission_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.save_mission(self.record)

    def test_list_missions(self):
        self.store.save_mission(sample_record("mission-002"))
        self.assertEqual(len(self.store.list_missions(limit=10)), 2)

    def test_invalid_list_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.list_missions(limit=True)

    def test_oversized_record_is_rejected(self):
        record = sample_record("mission-large")
        record["extra"] = "x" * 1_000_001
        with self.assertRaises(ValueError):
            self.store.save_mission(record)

    def test_nan_is_rejected(self):
        record = sample_record("mission-nan")
        record["extra"] = float("nan")
        with self.assertRaises(ValueError):
            self.store.save_mission(record)

    def test_feedback_is_persisted(self):
        feedback_id = self.store.record_feedback(
            "mission-001",
            {"rating": 5, "helpful": True, "comments": "Useful plan"},
        )
        items = self.store.list_feedback("mission-001")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["feedback_id"], feedback_id)
        self.assertEqual(items[0]["feedback"]["rating"], 5)

    def test_invalid_feedback_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_feedback("mission-001", {"rating": 9})

    def test_boolean_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_feedback("mission-001", {"rating": True})

    def test_unknown_feedback_field_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.record_feedback(
                "mission-001", {"rating": 4, "secret": "not allowed"}
            )

    def test_feedback_for_unknown_mission_is_rejected(self):
        with self.assertRaises(KeyError):
            self.store.record_feedback("missing", {"helpful": True})

    def test_completed_task_requires_evidence(self):
        with self.assertRaises(ValueError):
            self.store.update_task_status(
                "mission-001", "resume", "completed"
            )

    def test_task_completion_and_history_are_saved(self):
        self.store.update_task_status(
            "mission-001",
            "resume",
            "completed",
            note="Resume draft reviewed",
        )
        loaded = self.store.get_mission("mission-001")
        task = loaded["plan"]["days"][0]["tasks"][0]
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["result"], "Resume draft reviewed")

        events = self.store.list_events("mission-001")
        self.assertEqual(events[-1]["event_type"], "task_status_changed")

    def test_unknown_task_is_rejected(self):
        with self.assertRaises(KeyError):
            self.store.update_task_status(
                "mission-001", "missing", "in_progress"
            )

    def test_completed_task_cannot_be_reopened_directly(self):
        self.store.update_task_status(
            "mission-001", "resume", "completed", note="Reviewed"
        )
        with self.assertRaises(ValueError):
            self.store.update_task_status(
                "mission-001", "resume", "pending"
            )

    def test_delete_removes_mission_and_related_data(self):
        self.store.record_feedback("mission-001", {"rating": 4})
        self.assertTrue(self.store.delete_mission("mission-001"))
        self.assertIsNone(self.store.get_mission("mission-001"))
        self.assertFalse(self.store.delete_mission("mission-001"))

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions only")
    def test_database_file_is_private(self):
        mode = stat.S_IMODE(self.store.path.stat().st_mode)
        self.assertEqual(mode, 0o600)

    def test_invalid_mission_id_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.get_mission("../outside")


if __name__ == "__main__":
    unittest.main()
