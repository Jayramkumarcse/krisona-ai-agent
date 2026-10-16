"""Tests for the KRISONA command-line interface."""

import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from krisona_ai import __main__ as cli
from krisona_ai.mission_store import MissionStore


class CLITests(unittest.TestCase):
    def test_empty_situation_returns_error(self):
        with patch("builtins.input", return_value=""):
            with redirect_stdout(StringIO()):
                self.assertEqual(cli.run_interactive(), 2)

    def test_run_saves_consistent_mission_id(self):
        workflow_result = {
            "status": "clarifying",
            "mission": {
                "mission_id": "mission-test-123",
                "status": "clarifying",
            },
            "decision": None,
            "next_step": "Clarify the goal.",
            "plan": None,
        }

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.sqlite3"

            with (
                patch.object(cli, "DB_PATH", database),
                patch(
                    "builtins.input",
                    side_effect=["Improve my spoken English", "0"],
                ),
                patch.object(
                    cli,
                    "run_mission_workflow",
                    return_value=workflow_result,
                ),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(cli.run_interactive(), 0)

            saved = MissionStore(database).get_mission("mission-test-123")

            self.assertIsNotNone(saved)
            self.assertEqual(
                saved["mission_id"],
                saved["workflow_result"]["mission"]["mission_id"],
            )

    def test_list_handles_empty_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "empty.sqlite3"

            with (
                patch.object(cli, "DB_PATH", database),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(cli.list_missions(), 0)


if __name__ == "__main__":
    unittest.main()
