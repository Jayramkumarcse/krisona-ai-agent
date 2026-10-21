"""Collect goal details interactively, one question at a time."""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any

from .mission_detector import detect_mission


DOMAIN_ALIASES = {
    "career": "career",
    "job": "career",
    "education": "education",
    "study": "education",
    "daily life": "daily_life",
    "daily_life": "daily_life",
    "daily": "daily_life",
    "productivity": "productivity",
}

DOMAIN_LABELS = {
    "career": "career",
    "education": "education",
    "daily_life": "daily life",
    "productivity": "productivity",
}


def _ask_optional_number(
    ask: Callable[[str], str],
    output: Callable[[str], None],
    prompt: str,
    minimum: float,
    maximum: float | None = None,
) -> float | None:
    """Ask for an optional finite number and validate its range."""
    while True:
        raw = ask(prompt).strip()

        if not raw:
            return None

        try:
            value = float(raw)
        except ValueError:
            output("Please enter a valid number, or press Enter to skip.")
            continue

        if not math.isfinite(value) or value < minimum:
            output(f"Enter a finite number >= {minimum}, or press Enter to skip.")
            continue

        if maximum is not None and value > maximum:
            output(f"Enter a number <= {maximum}, or press Enter to skip.")
            continue

        return value


def collect_goal_clarifications(
    situation: str,
    *,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Collect missing domain, goal, deadline, criteria, time, and constraints.

    Blank optional answers remain unspecified. Daily availability defaults
    to 120 minutes when the user presses Enter.
    """
    ask = input if input_fn is None else input_fn
    output = print if output_fn is None else output_fn

    if not isinstance(situation, str) or not situation.strip():
        raise ValueError("Please describe your goal or situation first.")

    original = situation.strip()
    detected = detect_mission(original)

    # Ask for the domain only when the detector cannot assign one.
    domain = detected["domain"]
    if domain == "other":
        while True:
            answer = ask(
                "Is this mainly about career, education, daily life, "
                "or productivity? "
            ).strip().casefold()

            domain = DOMAIN_ALIASES.get(answer)
            if domain:
                break

            output(
                "Please choose career, education, daily life, or productivity."
            )

    # Ask for a specific outcome only when one was not detected.
    goal = detected["goal"]
    if goal is None:
        while True:
            answer = ask(
                "What specific outcome would you like to achieve? "
            ).strip()

            if not answer:
                output("Please enter a goal, even if it is a first draft.")
                continue

            answer_detection = detect_mission(answer)
            goal = answer_detection["goal"] or answer
            break

    deadline = detected["time_horizon"]
    if deadline is None:
        answer = ask(
            "By when would you like to achieve this? "
            "(For example, within 8 weeks; press Enter if unsure): "
        ).strip()

        if answer.casefold() not in {
            "", "not sure", "unsure", "unknown", "flexible", "no deadline"
        }:
            deadline = answer

    success_criteria = ask(
        "What measurable result will tell you that you succeeded? "
        "(Press Enter to leave this unspecified): "
    ).strip() or None

    daily_raw = ask(
        "How many minutes per day can you realistically spend? "
        "(1-1440; Enter uses 120): "
    ).strip()

    if not daily_raw:
        daily_capacity_minutes = 120
    else:
        while True:
            try:
                daily_capacity_minutes = int(daily_raw)
            except ValueError:
                daily_capacity_minutes = 0

            if 1 <= daily_capacity_minutes <= 1440:
                break

            daily_raw = ask(
                "Enter a whole number from 1 to 1440, or press Enter for 120: "
            ).strip()

            if not daily_raw:
                daily_capacity_minutes = 120
                break

    # These are the hard constraints currently supported by the decision engine.
    constraints: dict[str, float] = {}

    max_cost = _ask_optional_number(
        ask, output,
        "What is your maximum budget/cost? (Enter to skip): ",
        0,
    )
    if max_cost is not None:
        constraints["max_cost"] = max_cost

    max_duration = _ask_optional_number(
        ask, output,
        "What is the maximum acceptable duration in days? (Enter to skip): ",
        0,
    )
    if max_duration is not None:
        constraints["max_duration_days"] = max_duration

    min_safety = _ask_optional_number(
        ask, output,
        "What minimum safety rating do you require (1-5)? "
        "(Enter to skip): ",
        1,
        5,
    )
    if min_safety is not None:
        constraints["min_safety"] = min_safety

    # Preserve the clarified goal as the final line because goal extraction
    # uses an explicit goal phrase at the end of the situation text.
    context_lines = [original]
    context_lines.append(f"User-selected domain: {DOMAIN_LABELS[domain]}.")

    if deadline:
        context_lines.append(f"Target deadline: {deadline}.")
    if success_criteria:
        context_lines.append(f"Success criteria: {success_criteria}.")
    context_lines.append(
        f"Daily available time: {daily_capacity_minutes} minutes."
    )
    if constraints:
        context_lines.append(f"User-confirmed hard constraints: {constraints}.")

    clarified_situation = "\n".join(
        context_lines + [f"My goal is to {goal.rstrip(' .!?')}."]
    )
    mission = detect_mission(clarified_situation)

    # A user-confirmed answer takes precedence over keyword classification.
    mission["domain"] = domain
    mission["goal"] = goal
    mission["deadline"] = deadline
    mission["time_horizon"] = deadline or mission["time_horizon"]
    mission["success_criteria"] = success_criteria
    mission.setdefault("context", {})
    mission["context"]["daily_available_minutes"] = daily_capacity_minutes

    if goal and domain != "other":
        mission["status"] = "identified"

    if goal:
        mission["missing_information"] = [
            item for item in mission["missing_information"]
            if item != "goal"
        ]
    if deadline:
        mission["missing_information"] = [
            item for item in mission["missing_information"]
            if item != "time_horizon"
        ]
    if success_criteria:
        mission["missing_information"] = [
            item for item in mission["missing_information"]
            if item != "success_criteria"
        ]

    return {
        "situation": clarified_situation,
        "mission": mission,
        "constraints": constraints,
        "daily_capacity_minutes": daily_capacity_minutes,
        "success_criteria": success_criteria,
        "deadline": deadline,
    }
