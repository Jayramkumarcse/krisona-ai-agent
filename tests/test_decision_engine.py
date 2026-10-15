"""Tests for the hardened KRISONA AI AGENT Decision Engine."""

import unittest

from krisona_ai.decision_engine import evaluate_options


def option(
    option_id,
    description,
    *,
    alignment=5,
    feasibility=4,
    safety=5,
    cost_fit=4,
    time_fit=4,
    cost=100,
    duration_days=10,
    risks=None,
):
    return {
        "id": option_id,
        "description": description,
        "goal_alignment": alignment,
        "feasibility": feasibility,
        "safety": safety,
        "cost_fit": cost_fit,
        "time_fit": time_fit,
        "cost": cost,
        "duration_days": duration_days,
        "risks": risks or [],
    }


class DecisionEngineTests(unittest.TestCase):

    def test_selects_highest_scoring_eligible_option(self):
        options = [
            option("a", "Take a short practical course", alignment=4),
            option("b", "Build a focused portfolio project", alignment=5),
        ]
        result = evaluate_options(options)
        self.assertEqual(result["status"], "recommended")
        self.assertEqual(result["selected_option_id"], "b")

    def test_hard_cost_limit_excludes_expensive_option(self):
        options = [
            option("paid", "Expensive course", cost=5000),
            option("free", "Use free learning resources", cost=0),
        ]
        result = evaluate_options(options, {"max_cost": 1000})
        self.assertEqual(result["selected_option_id"], "free")

    def test_unknown_cost_requires_clarification(self):
        result = evaluate_options(
            [option("unknown", "Unknown cost", cost=None)],
            {"max_cost": 1000},
        )
        self.assertEqual(result["status"], "clarifying")
        self.assertIsNone(result["selected_option_id"])
        self.assertIn("unknown.cost", result["missing_information"])

    def test_unknown_competitor_prevents_premature_recommendation(self):
        options = [
            option("known", "Known cost", alignment=3, cost=100),
            option("unknown", "Unknown cost", alignment=5, cost=None),
        ]
        result = evaluate_options(options, {"max_cost": 1000})
        self.assertEqual(result["status"], "clarifying")
        self.assertIsNone(result["selected_option_id"])

    def test_duration_constraint_is_respected(self):
        options = [
            option("slow", "Long plan", duration_days=60),
            option("fast", "Short plan", duration_days=7),
        ]
        result = evaluate_options(options, {"max_duration_days": 14})
        self.assertEqual(result["selected_option_id"], "fast")

    def test_minimum_safety_rating_is_respected(self):
        options = [
            option("unsafe", "Low safety rating", safety=1),
            option("safe", "Higher safety rating", safety=5),
        ]
        result = evaluate_options(options, {"min_safety": 4})
        self.assertEqual(result["selected_option_id"], "safe")

    def test_no_feasible_option_returns_no_recommendation(self):
        result = evaluate_options(
            [option("costly", "Over budget", cost=500)],
            {"max_cost": 100},
        )
        self.assertEqual(result["status"], "no_feasible_option")
        self.assertIsNone(result["recommendation"])

    def test_empty_options_requests_clarification(self):
        result = evaluate_options([])
        self.assertEqual(result["status"], "clarifying")

    def test_invalid_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option("bad", "Bad rating", alignment=8)])

    def test_non_finite_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option("bad", "NaN rating", alignment=float("nan"))])

    def test_boolean_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option("bad", "Boolean rating", alignment=True)])

    def test_negative_constraint_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option("a", "Option")], {"max_cost": -1})

    def test_non_finite_constraint_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option("a", "Option")], {"max_cost": float("inf")})

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([
                option("same", "First"),
                option("same", "Second"),
            ])

    def test_unknown_option_field_is_rejected(self):
        bad = option("a", "Option")
        bad["goal_alingment"] = 5
        with self.assertRaises(ValueError):
            evaluate_options([bad])

    def test_oversized_option_list_is_rejected(self):
        options = [option(str(i), "Option") for i in range(101)]
        with self.assertRaises(ValueError):
            evaluate_options(options)

    def test_oversized_description_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option("a", "x" * 1001)])

    def test_oversized_risk_list_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_options([option(
                "a", "Option", risks=[f"risk {i}" for i in range(21)]
            )])

    def test_non_list_options_are_rejected(self):
        with self.assertRaises(TypeError):
            evaluate_options("not a list")

    def test_non_mapping_constraints_are_rejected(self):
        with self.assertRaises(TypeError):
            evaluate_options([option("a", "Option")], ["max_cost"])

    def test_rationale_disclaims_probability(self):
        result = evaluate_options([option("a", "Option")])
        self.assertIn("not probabilities", result["scoring_note"])


if __name__ == "__main__":
    unittest.main()
