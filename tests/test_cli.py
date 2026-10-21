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
        details = {
            "situation": "Improve my spoken English",
            "mission": {
                "domain": "daily_life",
                "goal": "improve my spoken English",
                "deadline": "within 8 weeks",
                "time_horizon": "within 8 weeks",
                "success_criteria": "Hold a five-minute conversation",
                "context": {},
                "missing_information": [],
            },
            "constraints": {},
            "daily_capacity_minutes": 30,
            "success_criteria": "Hold a five-minute conversation",
            "deadline": "within 8 weeks",
        }

        advice = {
            "status": "advice_ready",
            "problem_type": "spoken_english",
            "title": "Build speaking confidence",
            "problem": "Improve my spoken English",
            "goal": "improve my spoken English",
            "deadline": "within 8 weeks",
            "recommended_approach": "Practise speaking regularly.",
            "options": [{
                "name": "Daily practice",
                "benefit": "Low cost",
                "tradeoff": "Needs consistency",
                "first_step": "Record a short voice note.",
            }],
            "action_plan": [{
                "when": "Today",
                "task": "Record a short voice note.",
            }],
            "success_measure": "Hold a five-minute conversation",
            "review": "Review progress after 7 days.",
            "limitations": "Suggestions are not guaranteed outcomes.",
        }

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.sqlite3"
            output = StringIO()

            with (
                patch.object(cli, "DB_PATH", database),
                patch.object(
                    cli,
                    "collect_goal_clarifications",
                    return_value=details,
                ),
                patch.object(
                    cli,
                    "generate_solution_advice",
                    return_value=advice,
                ),
                patch(
                    "builtins.input",
                    side_effect=["Improve my spoken English"],
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(cli.run_interactive(), 0)

            mission_line = next(
                line for line in output.getvalue().splitlines()
                if line.startswith("Mission ID: ")
            )
            mission_id = mission_line.partition(": ")[2]
            saved = MissionStore(database).get_mission(mission_id)

            self.assertIsNotNone(saved)
            self.assertEqual(saved["mission_id"], mission_id)
            self.assertEqual(
                saved["workflow_result"]["mission"]["mission_id"],
                mission_id,
            )
            self.assertEqual(
                saved["workflow_result"]["status"],
                "advice_ready",
            )

    def test_list_handles_empty_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "empty.sqlite3"

            with (
                patch.object(cli, "DB_PATH", database),
                redirect_stdout(StringIO()),
            ):
                self.assertEqual(cli.list_missions(), 0)


    def test_progress_cli_commands_record_and_report(self):
        mission_id = "mission-cli-progress-test"

        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "progress.sqlite3"

            MissionStore(database).save_mission({
                "mission_id": mission_id,
                "created_at": "2026-01-01T00:00:00+00:00",
                "situation": "Improve spoken English",
                "workflow_result": {
                    "status": "advice_ready",
                    "mission": {
                        "mission_id": mission_id,
                        "goal": "improve spoken English",
                        "domain": "daily_life",
                    },
                },
            })

            answers = [
                "10",
                "Recorded a voice note in English",
                "y",
                "Finding the right words",
                "3",
            ]

            with (
                patch.object(cli, "DB_PATH", database),
                patch("builtins.input", side_effect=answers),
                redirect_stdout(StringIO()) as checkin_output,
            ):
                self.assertEqual(
                    cli.main([
                        "checkin", "--mission-id", mission_id
                    ]),
                    0,
                )

            self.assertIn(
                "Check-in saved successfully",
                checkin_output.getvalue(),
            )

            with (
                patch.object(cli, "DB_PATH", database),
                redirect_stdout(StringIO()) as progress_output,
            ):
                self.assertEqual(
                    cli.main([
                        "progress", "--mission-id", mission_id
                    ]),
                    0,
                )

            self.assertIn('"practice_minutes": 10', progress_output.getvalue())
            self.assertIn('"checkins": 1', progress_output.getvalue())

            with (
                patch.object(cli, "DB_PATH", database),
                redirect_stdout(StringIO()) as review_output,
            ):
                self.assertEqual(
                    cli.main([
                        "review", "--mission-id", mission_id
                    ]),
                    0,
                )

            self.assertIn(
                '"weekly_review_ready"',
                review_output.getvalue(),
            )


if __name__ == "__main__":
    unittest.main()
