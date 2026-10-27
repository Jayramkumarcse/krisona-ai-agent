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

    def test_extracts_stated_budget_daily_time_and_deadline(self):
        answers = iter(["", "3"])
        prompts = []
        messages = []

        def ask(prompt):
            prompts.append(prompt)
            return next(answers)

        result = collect_goal_clarifications(
            (
                "I want to improve my spoken English for job interviews "
                "within 30 days. My budget is ₹0, and I can practice "
                "for 30 minutes each day."
            ),
            input_fn=ask,
            output_fn=messages.append,
        )

        self.assertEqual(result["daily_capacity_minutes"], 30)
        self.assertEqual(result["deadline"], "within 30 days")
        self.assertEqual(
            result["constraints"],
            {
                "max_cost": 0.0,
                "max_duration_days": 30.0,
                "min_safety": 3.0,
            },
        )
        self.assertFalse(
            any("How many minutes per day" in prompt for prompt in prompts)
        )
        self.assertFalse(
            any("maximum budget in INR" in prompt for prompt in prompts)
        )
        self.assertTrue(
            any("30 minutes per day" in message for message in messages)
        )
        self.assertTrue(
            any("maximum budget: INR 0" in message for message in messages)
        )

    def test_accepts_daily_time_with_units_at_prompt(self):
        answers = iter(["", "30 minutes per day", "", ""])
        result = collect_goal_clarifications(
            "I want to improve my career within 4 weeks",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )

        self.assertEqual(result["daily_capacity_minutes"], 30)
        self.assertEqual(
            result["constraints"],
            {"max_duration_days": 28.0},
        )

    def test_ambiguous_daily_time_is_not_assumed(self):
        answers = iter(["", "30", "", "", ""])
        result = collect_goal_clarifications(
            "I want to improve my career in 4 weeks. I have 30 or 60 minutes per day.",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )
        self.assertEqual(result["daily_capacity_minutes"], 30)

    def test_accepts_natural_domain_answer_about_interviews(self):
        answers = iter(["for interviews", "", "", "30", "0", "30", "3"])
        result = collect_goal_clarifications(
            "I want to improve my spoken English",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )

        self.assertEqual(result["mission"]["domain"], "career")
        self.assertEqual(result["daily_capacity_minutes"], 30)
        self.assertEqual(
            result["constraints"],
            {
                "max_cost": 0.0,
                "max_duration_days": 30.0,
                "min_safety": 3.0,
            },
        )

    def test_uses_default_daily_capacity_and_allows_optional_skips(self):
        answers = iter(["", "30", "", "", ""])
        result = collect_goal_clarifications(
            "I want to improve my career within 4 weeks",
            input_fn=lambda _prompt: next(answers),
            output_fn=lambda _message: None,
        )

        self.assertEqual(result["daily_capacity_minutes"], 30)
        self.assertEqual(
            result["constraints"],
            {"max_duration_days": 28.0},
        )

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
