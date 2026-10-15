"""Deterministic daily action planner for KRISONA AI AGENT."""

from __future__ import annotations

import re
from datetime import date
from typing import Any


MAX_TASKS = 100
MAX_DAILY_MINUTES = 1440
MAX_TASK_ID_LENGTH = 80
MAX_TITLE_LENGTH = 200
MAX_CRITERIA_LENGTH = 500

TASK_FIELDS = {
    "id",
    "title",
    "duration_minutes",
    "priority",
    "depends_on",
    "completion_criteria",
}
TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _clean_text(value: Any, field: str, limit: int) -> str:
    """Validate bounded, non-empty single-line text."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")

    result = value.strip()

    if not result:
        raise ValueError(f"{field} must not be empty.")

    if len(result) > limit:
        raise ValueError(f"{field} exceeds the {limit}-character limit.")

    if any(ord(char) < 32 or ord(char) == 127 for char in result):
        raise ValueError(f"{field} contains prohibited control characters.")

    return result


def _validate_start_date(value: date | str | None) -> date:
    if value is None:
        return date.today()

    if type(value) is date:
        return value

    if not isinstance(value, str) or not ISO_DATE_PATTERN.fullmatch(value):
        raise ValueError("start_date must use YYYY-MM-DD format.")

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("start_date is not a valid calendar date.") from exc


def _validate_task(raw: Any, index: int, capacity: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Task {index} must be an object.")

    if any(not isinstance(key, str) for key in raw):
        raise ValueError(f"Task {index} contains an invalid field name.")

    unknown = set(raw) - TASK_FIELDS
    if unknown:
        raise ValueError(
            f"Task {index} contains unsupported fields: "
            f"{', '.join(sorted(unknown))}."
        )

    required = {
        "id",
        "title",
        "duration_minutes",
        "priority",
        "completion_criteria",
    }
    missing = required - set(raw)
    if missing:
        raise ValueError(
            f"Task {index} is missing required fields: "
            f"{', '.join(sorted(missing))}."
        )

    task_id = raw["id"]
    if (
        not isinstance(task_id, str)
        or not TASK_ID_PATTERN.fullmatch(task_id)
        or len(task_id) > MAX_TASK_ID_LENGTH
    ):
        raise ValueError(
            f"Task {index} id must use letters, digits, dots, "
            "underscores, or hyphens."
        )

    title = _clean_text(raw["title"], f"{task_id}.title", MAX_TITLE_LENGTH)
    criteria = _clean_text(
        raw["completion_criteria"],
        f"{task_id}.completion_criteria",
        MAX_CRITERIA_LENGTH,
    )

    duration = raw["duration_minutes"]
    if isinstance(duration, bool) or not isinstance(duration, int):
        raise ValueError(f"{task_id}.duration_minutes must be an integer.")

    if not 1 <= duration <= MAX_DAILY_MINUTES:
        raise ValueError(
            f"{task_id}.duration_minutes must be between 1 and "
            f"{MAX_DAILY_MINUTES}."
        )

    if duration > capacity:
        raise ValueError(
            f"{task_id} needs {duration} minutes, exceeding the "
            f"daily capacity of {capacity}. Split the task or increase capacity."
        )

    priority = raw["priority"]
    if (
        isinstance(priority, bool)
        or not isinstance(priority, int)
        or not 1 <= priority <= 5
    ):
        raise ValueError(f"{task_id}.priority must be an integer from 1 to 5.")

    dependencies = raw.get("depends_on", [])
    if not isinstance(dependencies, list) or len(dependencies) > MAX_TASKS:
        raise ValueError(f"{task_id}.depends_on must be a bounded list.")

    if any(
        not isinstance(dep, str) or not TASK_ID_PATTERN.fullmatch(dep)
        for dep in dependencies
    ):
        raise ValueError(f"{task_id}.depends_on contains an invalid task id.")

    if len(set(dependencies)) != len(dependencies):
        raise ValueError(f"{task_id}.depends_on contains duplicate ids.")

    if task_id in dependencies:
        raise ValueError(f"{task_id} cannot depend on itself.")

    return {
        "id": task_id,
        "title": title,
        "duration_minutes": duration,
        "priority": priority,
        "depends_on": list(dependencies),
        "completion_criteria": criteria,
    }


def _validate_dependencies(tasks: list[dict[str, Any]]) -> None:
    """Reject missing references and dependency cycles."""
    by_id = {task["id"]: task for task in tasks}

    for task in tasks:
        for dependency in task["depends_on"]:
            if dependency not in by_id:
                raise ValueError(
                    f"{task['id']} depends on unknown task {dependency}."
                )

    # Kahn's algorithm detects cycles without recursive traversal.
    pending = {
        task["id"]: set(task["depends_on"])
        for task in tasks
    }
    completed: set[str] = set()

    while True:
        ready = [
            task_id
            for task_id, dependencies in pending.items()
            if task_id not in completed and dependencies <= completed
        ]

        if not ready:
            break

        completed.update(ready)

    if len(completed) != len(tasks):
        raise ValueError("Task dependencies contain a cycle.")


def build_daily_plan(
    tasks: list[dict[str, Any]],
    daily_capacity_minutes: int = 120,
    start_date: date | str | None = None,
) -> dict[str, Any]:
    """
    Schedule supplied tasks across days within a daily time budget.

    Priority 1 is highest. Dependencies must be scheduled before the
    dependent task; tasks may follow one another on the same day.
    This function does not execute tasks or verify completion.
    """
    if not isinstance(tasks, list):
        raise TypeError("tasks must be a list.")

    if len(tasks) > MAX_TASKS:
        raise ValueError(f"At most {MAX_TASKS} tasks are allowed.")

    capacity = daily_capacity_minutes
    if (
        isinstance(capacity, bool)
        or not isinstance(capacity, int)
        or not 1 <= capacity <= MAX_DAILY_MINUTES
    ):
        raise ValueError(
            f"daily_capacity_minutes must be an integer from 1 to "
            f"{MAX_DAILY_MINUTES}."
        )

    plan_start = _validate_start_date(start_date)

    if not tasks:
        return {
            "status": "clarifying",
            "start_date": plan_start.isoformat(),
            "daily_capacity_minutes": capacity,
            "days": [],
            "total_tasks": 0,
            "total_estimated_minutes": 0,
            "missing_information": ["tasks"],
            "clarifying_questions": [
                "Which concrete tasks will help achieve the goal?"
            ],
        }

    validated = [
        _validate_task(task, index, capacity)
        for index, task in enumerate(tasks)
    ]

    ids = [task["id"] for task in validated]
    if len(set(ids)) != len(ids):
        raise ValueError("Task ids must be unique.")

    _validate_dependencies(validated)

    remaining = {task["id"]: task for task in validated}
    scheduled_ids: set[str] = set()
    days: list[dict[str, Any]] = []
    day_index = 0

    while remaining:
        current_day = plan_start.fromordinal(plan_start.toordinal() + day_index)
        used_minutes = 0
        scheduled_today: set[str] = set()
        day_tasks: list[dict[str, Any]] = []

        while True:
            ready = [
                task for task in remaining.values()
                if set(task["depends_on"]) <= (scheduled_ids | scheduled_today)
            ]
            ready.sort(key=lambda task: (task["priority"], task["id"]))

            chosen = next(
                (
                    task for task in ready
                    if task["duration_minutes"] <= capacity - used_minutes
                ),
                None,
            )

            if chosen is None:
                break

            used_minutes += chosen["duration_minutes"]
            scheduled_today.add(chosen["id"])
            del remaining[chosen["id"]]

            day_tasks.append({
                **chosen,
                "sequence": len(day_tasks) + 1,
                "status": "pending",
            })

        if not day_tasks:
            # Validated tasks fit the daily capacity and the dependency
            # graph is acyclic, so reaching this state indicates a bug.
            raise RuntimeError("Planner could not schedule any ready task.")

        days.append({
            "date": current_day.isoformat(),
            "used_minutes": used_minutes,
            "remaining_minutes": capacity - used_minutes,
            "tasks": day_tasks,
        })

        scheduled_ids.update(scheduled_today)
        day_index += 1

    return {
        "status": "planned",
        "start_date": plan_start.isoformat(),
        "daily_capacity_minutes": capacity,
        "days": days,
        "total_tasks": len(validated),
        "total_estimated_minutes": sum(
            task["duration_minutes"] for task in validated
        ),
        "missing_information": [],
        "notes": [
            "Priority 1 is highest; tasks are scheduled using supplied estimates.",
            "A pending task is not evidence that the task has been completed.",
            "Review the plan when priorities, capacity, or dependencies change.",
        ],
    }
