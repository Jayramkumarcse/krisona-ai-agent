"""Collect goal details interactively, one question at a time."""

from __future__ import annotations

import math
import re
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


_DAILY_TIME_PATTERN = re.compile(
    r"\b(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>minutes?|mins?|hours?|hrs?)\s*"
    r"(?P<cadence>per day|a day|each day|every day|daily|/\s*day)\b",
    re.IGNORECASE,
)

_BUDGET_CUE = re.compile(
    r"\b(?:budget|spend(?:ing)?|cost)\b",
    re.IGNORECASE,
)

_MONEY_PATTERNS = (
    re.compile(r"₹\s*(?P<amount>\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bINR\s*(?P<amount>\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"\bRs\.?\s*(?P<amount>\d[\d,]*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(
        r"\b(?P<amount>\d[\d,]*(?:\.\d+)?)\s*"
        r"(?:INR\b|rupees?\b|Rs\.?)",
        re.IGNORECASE,
    ),
)


def _extract_daily_capacity_minutes(text: str) -> int | None:
    """Return one unambiguous daily time limit, in whole minutes."""
    # Do not select one side of an explicit numeric alternative such as
    # "30 or 60 minutes per day"; ask the user to resolve the ambiguity.
    ambiguous_alternative = re.search(
        r"\b\d+(?:\.\d+)?\s+(?:or|and)\s+"
        r"\d+(?:\.\d+)?\s*"
        r"(?:minutes?|mins?|hours?|hrs?)\s*"
        r"(?:per day|a day|each day|every day|daily|/\s*day)\b",
        text,
        flags=re.IGNORECASE,
    )
    if ambiguous_alternative:
        return None

    matches = list(_DAILY_TIME_PATTERN.finditer(text))
    if not matches:
        return None

    values = set()
    for match in matches:
        amount = float(match.group("amount"))
        unit = match.group("unit").casefold()

        if unit.startswith(("hour", "hr")):
            amount *= 60

        if not amount.is_integer() or not 1 <= amount <= 1440:
            return None

        values.add(int(amount))

    return values.pop() if len(values) == 1 else None



_DAILY_INPUT_PATTERN = re.compile(
    r"^(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>minutes?|mins?|hours?|hrs?)?\s*"
    r"(?:per day|a day|each day|every day|daily|/\s*day)?$",
    re.IGNORECASE,
)


def _parse_daily_capacity_input(raw: str) -> int | None:
    """Parse daily availability supplied as a number or a duration phrase."""
    inferred = _extract_daily_capacity_minutes(raw)
    if inferred is not None:
        return inferred

    match = _DAILY_INPUT_PATTERN.fullmatch(raw.strip())
    if not match:
        return None

    amount = float(match.group("amount"))
    unit = (match.group("unit") or "minutes").casefold()

    if unit.startswith(("hour", "hr")):
        amount *= 60

    if not amount.is_integer() or not 1 <= amount <= 1440:
        return None

    return int(amount)


def _extract_max_budget_inr(text: str) -> float | None:
    """Return one unambiguous currency amount associated with a budget cue."""
    values = set()

    for pattern in _MONEY_PATTERNS:
        for match in pattern.finditer(text):
            start, end = match.span()
            nearby = text[max(0, start - 40):min(len(text), end + 40)]

            if not _BUDGET_CUE.search(nearby):
                continue

            amount = float(match.group("amount").replace(",", ""))
            if not math.isfinite(amount) or amount < 0:
                return None

            values.add(amount)

    return next(iter(values)) if len(values) == 1 else None


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



_DURATION_PATTERN = re.compile(
    r"\b(?P<amount>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>days?|weeks?|months?|years?)\b",
    re.IGNORECASE,
)


def _extract_duration_days(text: str | None) -> float | None:
    """Convert an explicit numeric duration into days, if unambiguous."""
    if not text:
        return None

    matches = list(_DURATION_PATTERN.finditer(text))
    if not matches:
        return None

    values = set()
    factors = {
        "day": 1,
        "week": 7,
        "month": 30,
        "year": 365,
    }

    for match in matches:
        amount = float(match.group("amount"))
        unit = match.group("unit").casefold().rstrip("s")
        days = amount * factors[unit]

        if not math.isfinite(days) or days <= 0:
            return None

        values.add(days)

    return next(iter(values)) if len(values) == 1 else None


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

            # Accept descriptive answers such as "for interviews" by using
            # the existing detector instead of requiring an exact label.
            if domain is None:
                answer_mission = detect_mission(answer)
                detected_domain = answer_mission.get("domain")
                if detected_domain in DOMAIN_LABELS:
                    domain = detected_domain

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

    detected_daily_capacity = _extract_daily_capacity_minutes(original)
    if detected_daily_capacity is not None:
        daily_capacity_minutes = detected_daily_capacity
        output(
            "Using stated daily availability: "
            f"{daily_capacity_minutes} minutes per day."
        )
    else:
        daily_raw = ask(
            "How many minutes per day can you realistically spend? "
            "(1-1440; e.g. 30 minutes per day; Enter uses 120): "
        ).strip()

        if not daily_raw:
            daily_capacity_minutes = 120
        else:
            while True:
                parsed_capacity = _parse_daily_capacity_input(daily_raw)
                if parsed_capacity is not None:
                    daily_capacity_minutes = parsed_capacity
                    break

                daily_raw = ask(
                    "Enter a value from 1 to 1440 minutes, "
                    "e.g. '30 minutes per day', or press Enter for 120: "
                ).strip()

                if not daily_raw:
                    daily_capacity_minutes = 120
                    break

    # These are the hard constraints currently supported by the decision engine.
    constraints: dict[str, float] = {}

    detected_budget = _extract_max_budget_inr(original)
    if detected_budget is None:
        max_cost = _ask_optional_number(
            ask, output,
            "What is your maximum budget in INR? (Enter to skip): ",
            0,
        )
    else:
        max_cost = detected_budget
        output(f"Using stated maximum budget: INR {max_cost:g}.")

    if max_cost is not None:
        constraints["max_cost"] = max_cost

    inferred_duration = _extract_duration_days(deadline)
    if inferred_duration is None:
        max_duration = _ask_optional_number(
            ask, output,
            "What is the maximum acceptable duration in days? (Enter to skip): ",
            0,
        )
    else:
        max_duration = inferred_duration
        output(
            "Using stated deadline as maximum duration: "
            f"{max_duration:g} days."
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
