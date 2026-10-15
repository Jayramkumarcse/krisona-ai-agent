"""Coordinate mission detection and decision support."""

from __future__ import annotations

from typing import Any

from .decision_engine import evaluate_options
from .mission_detector import detect_mission

MAX_SITUATION_LENGTH = 5_000


def process_situation(
    situation: str,
    options: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Analyze a situation and evaluate supplied candidate actions.

    Candidate actions are supplied by the caller; this module does not
    invent options or execute external actions.
    """
    if not isinstance(situation, str):
        raise TypeError("situation must be a string.")

    text = situation.strip()

    if not text:
        raise ValueError("Please describe your situation.")

    if len(text) > MAX_SITUATION_LENGTH:
        raise ValueError(
            f"situation must not exceed {MAX_SITUATION_LENGTH} characters."
        )

    if options is not None and not isinstance(options, list):
        raise TypeError("options must be a list or None.")

    if constraints is not None and not isinstance(constraints, dict):
        raise TypeError("constraints must be a dictionary or None.")

    mission = detect_mission(text)

    # Do not recommend an action when the mission itself needs clarification.
    if mission["status"] == "clarifying":
        return {
            "status": "clarifying",
            "mission": mission,
            "decision": None,
            "next_step": mission["next_step"],
        }

    # No supplied options means the engine must ask for candidate actions.
    decision = evaluate_options(
        options if options is not None else [],
        constraints,
    )

    if decision["status"] == "recommended":
        status = "recommendation_ready"
        next_step = (
            "Review the recommendation and confirm that it fits your "
            "goal and circumstances before planning execution."
        )
    elif decision["status"] == "no_feasible_option":
        status = "no_feasible_option"
        next_step = (
            "Review the constraints or provide alternative candidate actions."
        )
    else:
        status = "clarifying"
        next_step = (
            "Provide the missing candidate actions or constraint information."
        )

    return {
        "status": status,
        "mission": mission,
        "decision": decision,
        "next_step": next_step,
    }
