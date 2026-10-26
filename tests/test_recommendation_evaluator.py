"""Tests for the repeatable recommendation evaluation suite."""

import unittest
from unittest.mock import patch

from krisona_ai.recommendation_evaluator import evaluate_cases


def option(option_id, alignment=5, cost=0):
    return {
        "id": option_id,
        "description": f"Option {option_id}",
        "goal_alignment": alignment,
        "feasibility": 4,
        "safety": 5,
        "cost_fit": 4,
        "time_fit": 4,
        "cost": cost,
        "duration_days": 3,
        "risks": [],
    }


class RecommendationEvaluatorTests(unittest.TestCase):

    def test_correct_case_passes(self):
        report = evaluate_cases([{
            "id": "basic",
            "expected_status": "recommended",
            "expected_option_id": "best",
            "constraints": {},
            "options": [option("best"), option("other", alignment=2)],
        }])
        self.assertEqual(report["passed_cases"], 1)
        self.assertEqual(report["failed_cases"], 0)

    def test_ineligible_selection_fails_even_when_expected(self):
        case = {
            "id": "blocked_option",
            "expected_status": "recommended",
            "expected_option_id": "blocked",
            "constraints": {},
            "options": [option("blocked")],
        }
        simulated_engine_result = {
            "status": "recommended",
            "selected_option_id": "blocked",
            "evaluated_options": [
                {"id": "blocked", "status": "ineligible"},
            ],
        }

        with patch(
            "krisona_ai.recommendation_evaluator.evaluate_options",
            return_value=simulated_engine_result,
        ):
            report = evaluate_cases([case])

        result = report["results"][0]
        self.assertTrue(result["status_match"])
        self.assertTrue(result["selection_match"])
        self.assertFalse(result["selected_option_is_eligible"])
        self.assertFalse(result["eligibility_match"])
        self.assertFalse(result["passed"])
        self.assertEqual(report["failed_cases"], 1)


    def test_wrong_expected_selection_is_a_failure(self):
        report = evaluate_cases([{
            "id": "wrong",
            "expected_status": "recommended",
            "expected_option_id": "wrong-option",
            "constraints": {},
            "options": [option("actual")],
        }])
        self.assertEqual(report["failed_cases"], 1)

    def test_abstention_is_evaluated(self):
        report = evaluate_cases([{
            "id": "unknown",
            "expected_status": "clarifying",
            "expected_option_id": None,
            "constraints": {"max_cost": 100},
            "options": [option("unknown", cost=None)],
        }])
        self.assertEqual(report["passed_cases"], 1)

    def test_duplicate_case_ids_are_rejected(self):
        case = {
            "id": "same",
            "expected_status": "recommended",
            "expected_option_id": "a",
            "constraints": {},
            "options": [option("a")],
        }
        with self.assertRaises(ValueError):
            evaluate_cases([case, case])

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cases([{
                "id": "bad",
                "expected_status": "guaranteed",
                "expected_option_id": None,
                "constraints": {},
                "options": [],
            }])

    def test_non_list_cases_are_rejected(self):
        with self.assertRaises(TypeError):
            evaluate_cases("invalid")

    def test_empty_cases_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cases([])

    def test_unknown_case_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cases([{
                "id": "bad",
                "expected_status": "clarifying",
                "expected_option_id": None,
                "constraints": {},
                "options": [],
                "execute_command": "not allowed",
            }])


if __name__ == "__main__":
    unittest.main()
