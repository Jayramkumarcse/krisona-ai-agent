"""Integration tests for the full mission workflow."""

import unittest

from krisona_ai.mission_workflow import run_mission_workflow


def option(option_id, description, cost=0, duration_days=3, alignment=5):
    return {
        "id": option_id,
        "description": description,
        "goal_alignment": alignment,
        "feasibility": 4,
        "safety": 5,
        "cost_fit": 5,
        "time_fit": 4,
        "cost": cost,
        "duration_days": duration_days,
        "risks": [],
    }


def task(task_id, title, duration=30, dependencies=None):
    return {
        "id": task_id,
        "title": title,
        "duration_minutes": duration,
        "priority": 1,
        "depends_on": dependencies or [],
        "completion_criteria": "Deliverable reviewed",
    }


class MissionWorkflowTests(unittest.TestCase):

    def test_full_workflow_produces_daily_plan(self):
        result = run_mission_workflow(
            "I want to get a job in 30 days.",
            options=[
                option("resume", "Prepare a targeted resume"),
                option("course", "Study a job-related course", alignment=4),
            ],
            tasks=[
                task("profile", "List target job roles"),
                task("resume", "Draft resume", dependencies=["profile"]),
            ],
            daily_capacity_minutes=60,
            start_date="2026-10-16",
        )

        self.assertEqual(result["status"], "plan_ready")
        self.assertEqual(result["mission"]["domain"], "career")
        self.assertEqual(
            result["decision"]["selected_option_id"], "resume"
        )
        self.assertEqual(result["plan"]["status"], "planned")

    def test_ambiguous_mission_does_not_produce_plan(self):
        result = run_mission_workflow(
            "I am not sure what to do next.",
            options=[option("a", "Take a possible action")],
            tasks=[task("a", "Do a task")],
        )

        self.assertEqual(result["status"], "clarifying")
        self.assertIsNone(result["decision"])
        self.assertIsNone(result["plan"])

    def test_missing_options_does_not_produce_plan(self):
        result = run_mission_workflow(
            "I want to get a job in 30 days.",
            tasks=[task("a", "Prepare a resume")],
        )

        self.assertEqual(result["status"], "clarifying")
        self.assertIsNone(result["plan"])

    def test_recommendation_without_tasks_requests_a_plan(self):
        result = run_mission_workflow(
            "I want to get a job in 30 days.",
            options=[option("resume", "Prepare a targeted resume")],
        )

        self.assertEqual(result["status"], "decision_ready_plan_needed")
        self.assertIsNone(result["plan"])

    def test_empty_tasks_request_clarification(self):
        result = run_mission_workflow(
            "I want to get a job in 30 days.",
            options=[option("resume", "Prepare a targeted resume")],
            tasks=[],
        )

        self.assertEqual(result["status"], "planning_clarification")
        self.assertEqual(result["plan"]["status"], "clarifying")

    def test_hard_constraint_selects_feasible_option_and_builds_plan(self):
        result = run_mission_workflow(
            "I want to get a job in 30 days.",
            options=[
                option("paid", "Paid course", cost=500),
                option("free", "Free resume practice", cost=0),
            ],
            constraints={"max_cost": 0},
            tasks=[task("resume", "Draft a resume")],
        )

        self.assertEqual(result["status"], "plan_ready")
        self.assertEqual(result["decision"]["selected_option_id"], "free")
        self.assertEqual(result["plan"]["status"], "planned")

    def test_invalid_task_dependency_is_rejected(self):
        with self.assertRaises(ValueError):
            run_mission_workflow(
                "I want to get a job in 30 days.",
                options=[option("resume", "Prepare a targeted resume")],
                tasks=[
                    task("apply", "Apply for jobs", dependencies=["missing"])
                ],
            )

    def test_daily_capacity_is_enforced(self):
        with self.assertRaises(ValueError):
            run_mission_workflow(
                "I want to get a job in 30 days.",
                options=[option("resume", "Prepare a targeted resume")],
                tasks=[task("resume", "Prepare a resume", duration=90)],
                daily_capacity_minutes=60,
            )


if __name__ == "__main__":
    unittest.main()
