"""Tests for interactive goal clarification."""

import unittest

from krisona_ai.goal_clarifier import collect_goal_clarifications
from krisona_ai.mission_detector import detect_mission


class GoalClarifierTests(unittest.TestCase):
    def test_collects_domain_and_missing_goal_details(self):
        answers = iter([
            "education",
            "Finish a five-minute English conversation",
            "within 8 weeks",
            "Hold a five-minute conversation with fewer pauses",
            "30",
            "0",
            "56",
            "3",
        ])

        result = collect_goal_clarifications(
            "I need help",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )

        self.assertEqual(result["mission"]["domain"], "education")
        self.assertEqual(
            result["mission"]["goal"],
            "Finish a five-minute English conversation",
        )
        self.assertEqual(result["deadline"], "within 8 weeks")
        self.assertEqual(result["daily_capacity_minutes"], 30)
        self.assertEqual(
            result["constraints"],
            {
                "max_cost": 0.0,
                "max_duration_days": 56.0,
                "min_safety": 3.0,
            },
        )
        self.assertEqual(
            result["success_criteria"],
            "Hold a five-minute conversation with fewer pauses",
        )

    def test_uses_default_daily_capacity_and_allows_optional_skips(self):
        answers = iter(["", "30", "", "", ""])
        result = collect_goal_clarifications(
            "I want to improve my career within 4 weeks",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )

        self.assertEqual(result["daily_capacity_minutes"], 30)
        self.assertEqual(result["constraints"], {})

    def test_selected_daily_life_domain_is_detected_consistently(self):
        answers = iter(["daily life", "", "", "", "", "", ""])
        result = collect_goal_clarifications(
            "I want to improve my spoken English",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )

        detected_again = detect_mission(result["situation"])
        self.assertEqual(detected_again["domain"], "daily_life")
        self.assertEqual(detected_again["status"], "identified")

    def test_rejects_empty_initial_situation(self):
        with self.assertRaisesRegex(ValueError, "describe your goal"):
            collect_goal_clarifications(
                " ",
                input_fn=lambda _prompt: "",
                output_fn=lambda _message: None,
            )


if __name__ == "__main__":
    unittest.main()
