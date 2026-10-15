"""Tests for the daily action planner."""

import unittest

from krisona_ai.action_planner import build_daily_plan


def task(
    task_id,
    title,
    duration=30,
    priority=3,
    depends_on=None,
    completion_criteria="Deliverable reviewed",
):
    return {
        "id": task_id,
        "title": title,
        "duration_minutes": duration,
        "priority": priority,
        "depends_on": depends_on or [],
        "completion_criteria": completion_criteria,
    }


class ActionPlannerTests(unittest.TestCase):

    def test_schedules_tasks_within_daily_capacity(self):
        result = build_daily_plan(
            [task("a", "Task A", 45), task("b", "Task B", 30)],
            daily_capacity_minutes=60,
            start_date="2026-10-16",
        )
        self.assertEqual(result["status"], "planned")
        self.assertEqual(len(result["days"]), 2)
        self.assertTrue(
            all(day["used_minutes"] <= 60 for day in result["days"])
        )

    def test_higher_priority_runs_first_when_capacity_allows(self):
        result = build_daily_plan(
            [
                task("later", "Lower priority", 20, priority=4),
                task("urgent", "Highest priority", 20, priority=1),
            ],
            daily_capacity_minutes=60,
            start_date="2026-10-16",
        )
        self.assertEqual(result["days"][0]["tasks"][0]["id"], "urgent")

    def test_dependency_is_scheduled_before_dependent_task(self):
        result = build_daily_plan(
            [
                task("publish", "Publish", 30, depends_on=["draft"]),
                task("draft", "Prepare draft", 30),
            ],
            daily_capacity_minutes=60,
            start_date="2026-10-16",
        )
        ids = [item["id"] for day in result["days"] for item in day["tasks"]]
        self.assertLess(ids.index("draft"), ids.index("publish"))

    def test_dependencies_may_be_scheduled_on_same_day_in_order(self):
        result = build_daily_plan(
            [
                task("b", "Second task", 30, depends_on=["a"]),
                task("a", "First task", 30),
            ],
            daily_capacity_minutes=60,
            start_date="2026-10-16",
        )
        items = result["days"][0]["tasks"]
        self.assertEqual([item["id"] for item in items], ["a", "b"])

    def test_empty_tasks_request_clarification(self):
        result = build_daily_plan([])
        self.assertEqual(result["status"], "clarifying")
        self.assertIn("tasks", result["missing_information"])

    def test_unknown_dependency_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([task("a", "Task A", depends_on=["missing"])])

    def test_dependency_cycle_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([
                task("a", "Task A", depends_on=["b"]),
                task("b", "Task B", depends_on=["a"]),
            ])

    def test_duplicate_task_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([
                task("same", "Task A"),
                task("same", "Task B"),
            ])

    def test_task_larger_than_daily_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan(
                [task("a", "Too long", duration=90)],
                daily_capacity_minutes=60,
            )

    def test_invalid_priority_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([task("a", "Task A", priority=0)])

    def test_boolean_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([task("a", "Task A", duration=True)])

    def test_unknown_task_field_is_rejected(self):
        invalid = task("a", "Task A")
        invalid["shell_command"] = "not allowed"
        with self.assertRaises(ValueError):
            build_daily_plan([invalid])

    def test_invalid_date_is_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([task("a", "Task A")], start_date="2026-99-99")

    def test_control_characters_in_title_are_rejected(self):
        with self.assertRaises(ValueError):
            build_daily_plan([task("a", "Bad\nTitle")])

    def test_too_many_tasks_are_rejected(self):
        tasks = [task(f"t{i}", "Task") for i in range(101)]
        with self.assertRaises(ValueError):
            build_daily_plan(tasks)

    def test_plan_records_pending_not_completed(self):
        result = build_daily_plan([task("a", "Task A")])
        self.assertEqual(result["days"][0]["tasks"][0]["status"], "pending")


if __name__ == "__main__":
    unittest.main()
