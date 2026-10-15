"""Coordinate mission detection, decisions, and daily planning."""

from __future__ import annotations

from datetime import date
from typing import Any

from .action_planner import build_daily_plan
from .mission_orchestrator import process_situation


def run_mission_workflow(
    situation: str,
    options: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
    tasks: list[dict[str, Any]] | None = None,
    daily_capacity_minutes: int = 120,
    start_date: date | str | None = None,
) -> dict[str, Any]:
    """Run the decision workflow and, when possible, produce a daily plan.

    Candidate options and action tasks must be provided by the caller.
    This workflow never executes tasks or marks them completed.
    """
    result = process_situation(
        situation=situation,
        options=options,
        constraints=constraints,
    )

    # Do not plan until the mission has a usable recommendation.
    if result["status"] != "recommendation_ready":
        result["plan"] = None
        return result

    # A valid decision does not automatically imply that its execution
    # tasks are known. Ask for tasks rather than inventing them.
    if tasks is None:
        result["status"] = "decision_ready_plan_needed"
        result["plan"] = None
        result["next_step"] = (
            "Provide concrete tasks, their estimated durations, priorities, "
            "dependencies, and completion criteria."
        )
        return result

    plan = build_daily_plan(
        tasks=tasks,
        daily_capacity_minutes=daily_capacity_minutes,
        start_date=start_date,
    )

    result["plan"] = plan

    if plan["status"] == "planned":
        result["status"] = "plan_ready"
        result["next_step"] = (
            "Review the proposed schedule and adjust it to your real "
            "availability before starting."
        )
    else:
        result["status"] = "planning_clarification"
        result["next_step"] = (
            plan["clarifying_questions"][0]
            if plan.get("clarifying_questions")
            else "Provide the missing planning information."
        )

    return result
