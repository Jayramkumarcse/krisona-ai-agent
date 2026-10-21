"""Tests for KRISONA's initial local solution advisor."""

import unittest

from krisona_ai.solution_advisor import generate_solution_advice


class SolutionAdvisorTests(unittest.TestCase):
    def test_spoken_english_problem_gets_relevant_advice(self):
        result = generate_solution_advice(
            "I want to improve my spoken English",
            daily_capacity_minutes=10,
            success_criteria="Hold a five-minute conversation",
        )

        self.assertEqual(result["status"], "advice_ready")
        self.assertEqual(result["problem_type"], "spoken_english")
        self.assertEqual(len(result["options"]), 3)
        self.assertIn("five-minute", result["success_measure"])
        self.assertIn("10 minutes", result["action_plan"][0]["task"])

    def test_time_management_problem_gets_small_steps(self):
        result = generate_solution_advice(
            "I keep procrastinating and cannot focus",
            daily_capacity_minutes=15,
        )

        self.assertEqual(result["problem_type"], "focus_and_time")
        self.assertEqual(len(result["action_plan"]), 3)
        self.assertIn("priority", result["action_plan"][0]["task"].lower())

    def test_unmatched_problem_gets_transparent_general_advice(self):
        result = generate_solution_advice(
            "I have a difficult decision to make",
            daily_capacity_minutes=30,
        )

        self.assertEqual(result["problem_type"], "general_problem_solving")
        self.assertEqual(result["status"], "advice_ready")
        self.assertIn("not guaranteed", result["limitations"])

    def test_empty_problem_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "describe the problem"):
            generate_solution_advice(" ")

    def test_invalid_daily_capacity_is_rejected(self):
        for value in (0, -1, 1441, True, 10.5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "whole number"):
                    generate_solution_advice(
                        "I want to study",
                        daily_capacity_minutes=value,
                    )


if __name__ == "__main__":
    unittest.main()
