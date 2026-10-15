"""Validated, rule-based decision engine for KRISONA AI AGENT."""

from __future__ import annotations

from math import isfinite
from typing import Any


WEIGHTS = {
    "goal_alignment": 0.35,
    "feasibility": 0.25,
    "safety": 0.20,
    "cost_fit": 0.10,
    "time_fit": 0.10,
}

RATING_FIELDS = tuple(WEIGHTS)
CONSTRAINT_FIELDS = {"max_cost", "max_duration_days", "min_safety"}

MAX_OPTIONS = 100
MAX_ID_LENGTH = 80
MAX_DESCRIPTION_LENGTH = 1000
MAX_RISKS = 20
MAX_RISK_LENGTH = 500

OPTION_FIELDS = {
    "id",
    "description",
    "cost",
    "duration_days",
    "risks",
    *RATING_FIELDS,
}


def _number(
    value: Any,
    field: str,
    minimum: float,
    maximum: float | None = None,
) -> float:
    """Accept finite numbers only; reject booleans and overflow."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number.")

    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field} is outside the supported range.") from exc

    if not isfinite(number) or number < minimum:
        raise ValueError(f"{field} must be finite and >= {minimum}.")

    if maximum is not None and number > maximum:
        raise ValueError(f"{field} must be <= {maximum}.")

    return number


def _score(option: dict[str, Any]) -> float:
    """Calculate a weighted score from validated user-supplied ratings."""
    total = sum(option[field] * weight for field, weight in WEIGHTS.items())
    return round(total / 5 * 100, 1)


def _validate_option(raw: Any, index: int) -> dict[str, Any]:
    """Validate and copy one candidate option."""
    if not isinstance(raw, dict):
        raise ValueError(f"Option {index} must be an object.")

    if any(not isinstance(key, str) for key in raw):
        raise ValueError(f"Option {index} contains a non-string field name.")

    unknown = set(raw) - OPTION_FIELDS
    if unknown:
        raise ValueError(
            f"Option {index} has unsupported fields: {', '.join(sorted(unknown))}."
        )

    option_id = raw.get("id")
    description = raw.get("description")

    if not isinstance(option_id, str):
        raise ValueError(f"Option {index} needs a string id.")

    option_id = option_id.strip()
    if (
        not option_id
        or len(option_id) > MAX_ID_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 for char in option_id)
    ):
        raise ValueError(f"Option {index} has an invalid id.")

    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"Option {option_id} needs a description.")

    description = description.strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(f"{option_id}.description is too long.")

    option = dict(raw)
    option["id"] = option_id
    option["description"] = description

    for field in RATING_FIELDS:
        if field not in option:
            raise ValueError(f"{option_id} is missing {field}.")
        option[field] = _number(
            option[field], f"{option_id}.{field}", 1, 5
        )

    for field in ("cost", "duration_days"):
        if field in option and option[field] is not None:
            option[field] = _number(
                option[field], f"{option_id}.{field}", 0
            )

    risks = option.get("risks", [])
    if not isinstance(risks, list) or len(risks) > MAX_RISKS:
        raise ValueError(
            f"{option_id}.risks must be a list with at most {MAX_RISKS} items."
        )

    validated_risks = []
    for risk in risks:
        if not isinstance(risk, str) or not risk.strip():
            raise ValueError(f"{option_id}.risks must contain non-empty strings.")
        if len(risk) > MAX_RISK_LENGTH:
            raise ValueError(f"A risk description for {option_id} is too long.")
        validated_risks.append(risk.strip())

    option["risks"] = validated_risks
    return option


def evaluate_options(
    options: list[dict[str, Any]],
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Compare candidate actions under explicit constraints.

    Scores are heuristic ratings supplied with each option. This module
    does not verify the truth of ratings or independently assess safety.
    """
    if not isinstance(options, list):
        raise TypeError("options must be a list.")

    if len(options) > MAX_OPTIONS:
        raise ValueError(f"At most {MAX_OPTIONS} options are allowed.")

    if not options:
        return {
            "status": "clarifying",
            "selected_option_id": None,
            "recommendation": None,
            "score": None,
            "rationale": None,
            "trade_offs": [],
            "evaluated_options": [],
            "missing_information": ["candidate_options"],
            "clarifying_questions": [
                "What possible actions could help achieve the goal?"
            ],
        }

    if constraints is None:
        constraints = {}

    if not isinstance(constraints, dict):
        raise TypeError("constraints must be a dictionary.")

    if any(not isinstance(key, str) for key in constraints):
        raise ValueError("Constraint names must be strings.")

    unknown = set(constraints) - CONSTRAINT_FIELDS
    if unknown:
        raise ValueError(
            f"Unsupported constraints: {', '.join(sorted(unknown))}."
        )

    limits = {}
    for name, value in constraints.items():
        if value is None:
            continue
        minimum = 1 if name == "min_safety" else 0
        maximum = 5 if name == "min_safety" else None
        limits[name] = _number(value, name, minimum, maximum)

    validated = []
    seen_ids = set()

    for index, raw in enumerate(options):
        option = _validate_option(raw, index)
        if option["id"] in seen_ids:
            raise ValueError(f"Duplicate option id: {option['id']}.")
        seen_ids.add(option["id"])
        validated.append(option)

    evaluated = []

    for option in validated:
        reasons = []
        missing = []

        if "max_cost" in limits:
            if option.get("cost") is None:
                missing.append(f"{option['id']}.cost")
            elif option["cost"] > limits["max_cost"]:
                reasons.append("Exceeds maximum allowed cost.")

        if "max_duration_days" in limits:
            if option.get("duration_days") is None:
                missing.append(f"{option['id']}.duration_days")
            elif option["duration_days"] > limits["max_duration_days"]:
                reasons.append("Exceeds maximum allowed duration.")

        if (
            "min_safety" in limits
            and option["safety"] < limits["min_safety"]
        ):
            reasons.append("Does not meet the minimum safety rating.")

        if reasons:
            status = "ineligible"
        elif missing:
            status = "needs_information"
        else:
            status = "eligible"

        evaluated.append({
            "id": option["id"],
            "description": option["description"],
            "score": _score(option),
            "status": status,
            "reasons": reasons,
            "missing_information": missing,
            "ratings": {field: option[field] for field in RATING_FIELDS},
            "cost": option.get("cost"),
            "duration_days": option.get("duration_days"),
            "risks": option["risks"],
        })

    evaluated.sort(key=lambda item: (
        {"eligible": 0, "needs_information": 1, "ineligible": 2}[
            item["status"]
        ],
        -item["score"],
        item["id"],
    ))

    uncertain = [
        item for item in evaluated if item["status"] == "needs_information"
    ]
    eligible = [
        item for item in evaluated if item["status"] == "eligible"
    ]
    missing_information = sorted({
        field
        for item in uncertain
        for field in item["missing_information"]
    })

    # Do not pick a winner while a potentially viable competitor cannot
    # be checked against an explicitly requested hard constraint.
    if uncertain:
        return {
            "status": "clarifying",
            "selected_option_id": None,
            "recommendation": None,
            "score": None,
            "rationale": (
                "One or more options need information before a fair "
                "constraint-based comparison is possible."
            ),
            "trade_offs": [],
            "evaluated_options": evaluated,
            "missing_information": missing_information,
            "clarifying_questions": [
                "Please provide the missing cost or duration values, "
                "then compare the options again."
            ],
            "weights": WEIGHTS.copy(),
            "scoring_note": (
                "Scores compare supplied ratings; they are not probabilities "
                "or guarantees of success."
            ),
        }

    if not eligible:
        return {
            "status": "no_feasible_option",
            "selected_option_id": None,
            "recommendation": None,
            "score": None,
            "rationale": "No option satisfies all supplied hard constraints.",
            "trade_offs": [],
            "evaluated_options": evaluated,
            "missing_information": [],
            "clarifying_questions": [
                "Would you like to review the constraints or consider "
                "different candidate actions?"
            ],
            "weights": WEIGHTS.copy(),
            "scoring_note": (
                "Scores compare supplied ratings; they are not probabilities "
                "or guarantees of success."
            ),
        }

    chosen = eligible[0]

    return {
        "status": "recommended",
        "selected_option_id": chosen["id"],
        "recommendation": chosen["description"],
        "score": chosen["score"],
        "rationale": (
            "This option has the highest weighted score among options "
            "that satisfy the supplied constraints. "
            f"Goal alignment: {chosen['ratings']['goal_alignment']}/5; "
            f"feasibility: {chosen['ratings']['feasibility']}/5; "
            f"safety rating: {chosen['ratings']['safety']}/5."
        ),
        "trade_offs": chosen["risks"],
        "evaluated_options": evaluated,
        "missing_information": [],
        "clarifying_questions": [],
        "weights": WEIGHTS.copy(),
        "scoring_note": (
            "Scores compare supplied ratings; they are not probabilities "
            "or guarantees of success."
        ),
    }
