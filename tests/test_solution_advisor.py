"""Tests for KRISONA's initial local solution advisor."""

import unittest

from krisona_ai.solution_advisor import (
    _assess_constraint_fit,
    generate_solution_advice,
)


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


    def test_unknown_option_metadata_is_not_claimed_feasible(self):
        result = generate_solution_advice(
            "I want to improve my spoken English",
            daily_capacity_minutes=30,
            deadline="within 8 weeks",
            constraints={"max_cost": 3000, "max_duration_days": 56},
        )

        self.assertEqual(result["status"], "advice_ready")
        self.assertEqual(result["constraint_status"], "needs_verification")
        self.assertEqual(len(result["options"]), 3)
        self.assertTrue(all(
            item["constraint_assessment"]["status"] == "needs_verification"
            for item in result["options"]
        ))
        self.assertTrue(result["constraint_notes"])

    def test_known_constraint_violations_are_excluded(self):
        options = [
            {
                "name": "Suitable",
                "cost": 50,
                "duration_days": 10,
                "safety": 4,
            },
            {
                "name": "Over budget",
                "cost": 200,
                "duration_days": 10,
                "safety": 4,
            },
            {
                "name": "Unknown safety",
                "cost": 20,
                "duration_days": 10,
            },
        ]

        eligible, excluded, status, notes = _assess_constraint_fit(
            options,
            {"max_cost": 100, "max_duration_days": 30, "min_safety": 3},
        )

        self.assertEqual([item["name"] for item in eligible],
                         ["Suitable", "Unknown safety"])
        self.assertEqual(len(excluded), 1)
        self.assertEqual(excluded[0]["name"], "Over budget")
        self.assertEqual(status, "partially_verified")
        self.assertTrue(notes)
        self.assertEqual(
            eligible[1]["constraint_assessment"]["checks"]["min_safety"],
            "unknown",
        )

    def test_fully_known_compliant_options_pass_constraints(self):
        eligible, excluded, status, notes = _assess_constraint_fit(
            [{
                "name": "Suitable",
                "cost": 50,
                "duration_days": 7,
                "safety": 4,
            }],
            {"max_cost": 100, "max_duration_days": 14, "min_safety": 3},
        )

        self.assertEqual(status, "within_limits")
        self.assertEqual(len(eligible), 1)
        self.assertEqual(excluded, [])
        self.assertEqual(notes, [])

    def test_invalid_constraints_are_rejected(self):
        for constraints in (
            {"max_cost": True},
            {"max_cost": -1},
            {"max_duration_days": float("inf")},
            {"min_safety": 0},
            {"unsupported_limit": 10},
        ):
            with self.subTest(constraints=constraints):
                with self.assertRaises(ValueError):
                    generate_solution_advice(
                        "I want to improve my spoken English",
                        constraints=constraints,
                    )

        with self.assertRaises(TypeError):
            generate_solution_advice(
                "I want to improve my spoken English",
                constraints=["max_cost"],
            )



if __name__ == "__main__":
    unittest.main()
