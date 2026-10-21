"""Read-only feedback analytics for evidence-based improvement."""

from __future__ import annotations

from typing import Any

from .mission_store import MissionStore


MAX_ANALYZED_MISSIONS = 100

SUPPORTED_DOMAINS = {
    "career",
    "education",
    "daily_life",
    "productivity",
    "other",
}


def _new_bucket() -> dict[str, Any]:
    return {
        "mission_count": 0,
        "feedback_count": 0,
        "rating_count": 0,
        "rating_total": 0,
        "helpfulness_count": 0,
        "helpful_count": 0,
    }


def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    rating_count = bucket["rating_count"]
    helpfulness_count = bucket["helpfulness_count"]

    return {
        "mission_count": bucket["mission_count"],
        "feedback_count": bucket["feedback_count"],
        "rating_count": rating_count,
        "average_rating": (
            round(bucket["rating_total"] / rating_count, 2)
            if rating_count else None
        ),
        "helpfulness_count": helpfulness_count,
        "helpful_count": bucket["helpful_count"],
        "helpful_rate_percent": (
            round(bucket["helpful_count"] / helpfulness_count * 100, 1)
            if helpfulness_count else None
        ),
    }


def summarize_feedback(
    store: MissionStore,
    limit: int = 100,
) -> dict[str, Any]:
    """Summarize explicit user feedback without exposing comments.

    The function is read-only: it does not modify missions, scoring
    rules, recommendation weights, or a machine-learning model.
    """
    if not isinstance(store, MissionStore):
        raise TypeError("store must be a MissionStore instance.")

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("limit must be an integer from 1 to 100.")

    if not 1 <= limit <= MAX_ANALYZED_MISSIONS:
        raise ValueError("limit must be an integer from 1 to 100.")

    missions = store.list_missions(limit=limit)
    overall = _new_bucket()
    domains: dict[str, dict[str, Any]] = {}

    for record in missions:
        if not isinstance(record, dict):
            continue

        mission = record.get("mission")
        if not isinstance(mission, dict):
            workflow = record.get("workflow_result", {})
            mission = (
                workflow.get("mission", {})
                if isinstance(workflow, dict)
                else {}
            )
        if not isinstance(mission, dict):
            mission = {}

        domain = mission.get("domain", record.get("domain", "other"))
        if domain not in SUPPORTED_DOMAINS:
            domain = "other"

        bucket = domains.setdefault(domain, _new_bucket())

        overall["mission_count"] += 1
        bucket["mission_count"] += 1

        mission_id = record.get("mission_id") or mission.get("mission_id")
        if not isinstance(mission_id, str):
            continue

        feedback_items = store.list_feedback(mission_id)

        for item in feedback_items:
            feedback = item.get("feedback", {})
            if not isinstance(feedback, dict):
                continue

            overall["feedback_count"] += 1
            bucket["feedback_count"] += 1

            rating = feedback.get("rating")
            if (
                isinstance(rating, int)
                and not isinstance(rating, bool)
                and 1 <= rating <= 5
            ):
                overall["rating_count"] += 1
                overall["rating_total"] += rating
                bucket["rating_count"] += 1
                bucket["rating_total"] += rating

            helpful = feedback.get("helpful")
            if isinstance(helpful, bool):
                overall["helpfulness_count"] += 1
                bucket["helpfulness_count"] += 1

                if helpful:
                    overall["helpful_count"] += 1
                    bucket["helpful_count"] += 1

    return {
        "status": (
            "summary_ready"
            if overall["feedback_count"]
            else "no_feedback"
        ),
        **_finalize_bucket(overall),
        "analyzed_mission_limit": limit,
        "domains": {
            name: _finalize_bucket(domains[name])
            for name in sorted(domains)
        },
        "notes": [
            "Feedback is self-reported and may be incomplete or biased.",
            "Ratings and helpfulness do not prove that a recommendation "
            "caused a particular outcome.",
            "Only up to the requested number of recently updated missions "
            "were analyzed.",
            "This analysis does not change recommendation rules or models.",
        ],
    }
