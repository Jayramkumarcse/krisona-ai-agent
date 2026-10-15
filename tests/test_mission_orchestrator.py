"""Integration tests for the mission orchestrator."""

import unittest

from krisona_ai.mission_orchestrator import process_situation


def candidate(option_id, description, alignment=5):
    return {
        "id": option_id,
        "description": description,
        "goal_alignment": alignment,
        "feasibility": 4,
        "safety": 5,
        "cost_fit": 4,
        "time_fit": 4,
        "cost": 0,
        "duration_days": 7,
        "risks": [],
    }


class MissionOrchestratorTests(unittest.TestCase):

    def test_connects_detection_and_decision(self):
        result = process_situation(
            "I want to get a job in 30 days.",
            options=[
                candidate("a", "Prepare a focused resume", alignment=5),
                candidate("b", "Browse jobs without a plan", alignment=2),
            ],
        )

        self.assertEqual(result["status"], "recommendation_ready")
        self.assertEqual(result["mission"]["domain"], "career")
        self.assertEqual(result["decision"]["selected_option_id"], "a")

    def test_ambiguous_mission_does_not_get_recommendation(self):
        result = process_situation(
            "I am not sure what to do next.",
            options=[candidate("a", "Take an action")],
        )

        self.assertEqual(result["status"], "clarifying")
        self.assertIsNone(result["decision"])
        self.assertEqual(result["mission"]["domain"], "other")

    def test_missing_options_requests_clarification(self):
        result = process_situation("I want to get a job in 30 days.")

        self.assertEqual(result["status"], "clarifying")
        self.assertIn(
            "candidate_options",
            result["decision"]["missing_information"],
        )

    def test_hard_constraint_is_passed_to_decision_engine(self):
        result = process_situation(
            "I want to get a job in 30 days.",
            options=[
                candidate("paid", "Expensive course"),
                candidate("free", "Free resume practice"),
            ],
            constraints={"max_cost": 0},
        )

        self.assertEqual(result["status"], "recommendation_ready")
        self.assertEqual(result["decision"]["selected_option_id"], "free")

    def test_blank_input_is_rejected(self):
        with self.assertRaises(ValueError):
            process_situation("   ")

    def test_non_string_input_is_rejected(self):
        with self.assertRaises(TypeError):
            process_situation(None)

    def test_oversized_input_is_rejected(self):
        with self.assertRaises(ValueError):
            process_situation("x" * 5001)

    def test_invalid_options_type_is_rejected(self):
        with self.assertRaises(TypeError):
            process_situation("I want to get a job in 30 days.", options="invalid")

    def test_invalid_constraints_type_is_rejected(self):
        with self.assertRaises(TypeError):
            process_situation(
                "I want to get a job in 30 days.",
                constraints=[],
            )


if __name__ == "__main__":
    unittest.main()
