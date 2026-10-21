"""Read-only progress summaries for recorded user check-ins."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .mission_store import MissionStore


def summarize_progress(
    store: MissionStore,
    mission_id: str,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Summarize saved check-ins overall and over the last seven dates."""
    if not isinstance(store, MissionStore):
        raise TypeError("store must be a MissionStore instance.")

    if today is None:
        today = date.today()
    if not isinstance(today, date):
        raise ValueError("today must be a date.")

    record = store.get_mission(mission_id)
    if record is None:
        raise KeyError(f"Unknown mission: {mission_id}")

    workflow = record.get("workflow_result", {})
    mission = workflow.get("mission", {}) if isinstance(workflow, dict) else {}
    if not isinstance(mission, dict):
        mission = {}

    entries = [
        event["data"]
        for event in store.list_events(mission_id)
        if event.get("event_type") == "progress_checkin"
        and isinstance(event.get("data"), dict)
    ]

    def metrics(items: list[dict[str, Any]]) -> dict[str, Any]:
        ratings = [
            item["self_rating"]
            for item in items
            if item.get("self_rating") is not None
        ]
        completed_count = sum(
            item.get("completed") is True for item in items
        )
        return {
            "checkins": len(items),
            "active_days": len({item["checkin_date"] for item in items}),
            "practice_minutes": sum(item["minutes"] for item in items),
            "completed_sessions": completed_count,
            "completion_rate_percent": (
                round(completed_count / len(items) * 100, 1)
                if items else None
            ),
            "average_self_rating": (
                round(sum(ratings) / len(ratings), 2)
                if ratings else None
            ),
        }

    cutoff = (today - timedelta(days=6)).isoformat()
    recent = [
        item for item in entries
        if cutoff <= item["checkin_date"] <= today.isoformat()
    ]

    return {
        "status": "progress_ready" if entries else "no_checkins",
        "mission_id": mission_id,
        "goal": mission.get("goal"),
        "overall": metrics(entries),
        "last_7_days": metrics(recent),
        "recent_entries": sorted(
            entries,
            key=lambda item: item["checkin_date"],
            reverse=True,
        )[:10],
        "interpretation_note": (
            "Metrics summarize recorded check-ins only. Missing records "
            "do not prove that no practice occurred. Self-ratings are "
            "subjective and are not objective skill assessments."
        ),
    }


def create_weekly_review(
    store: MissionStore,
    mission_id: str,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Suggest an adjustment based only on the recorded seven-day summary."""
    report = summarize_progress(store, mission_id, today=today)
    week = report["last_7_days"]

    if week["checkins"] == 0:
        recommendation = (
            "No check-ins were recorded in the last seven days. Record your "
            "next session first; missing records do not prove no practice."
        )
    elif week["completion_rate_percent"] < 50:
        recommendation = (
            "Fewer than half of recorded sessions were marked complete. "
            "Try a smaller minimum session and record what made practice hard."
        )
    elif (
        week["average_self_rating"] is not None
        and week["average_self_rating"] <= 2
    ):
        recommendation = (
            "Practice feels difficult according to your recent self-ratings. "
            "Try shorter sessions, easier material, or a conversation partner."
        )
    else:
        recommendation = (
            "Continue a realistic routine. Choose one measurable target "
            "for next week and compare it with your next review."
        )

    return {
        "status": "weekly_review_ready",
        "mission_id": mission_id,
        "last_7_days": week,
        "recommendation": recommendation,
        "interpretation_note": report["interpretation_note"],
    }
