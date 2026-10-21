"""Interactive command-line interface for KRISONA AI AGENT."""

from __future__ import annotations

import argparse
import json
import math
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .decision_engine import RATING_FIELDS
from .goal_clarifier import collect_goal_clarifications
from .solution_advisor import generate_solution_advice
from .mission_store import MissionStore
from .feedback_analyzer import summarize_feedback
from .progress_tracker import create_weekly_review, summarize_progress


DB_PATH = Path(".local_data/krisona.sqlite3")
MAX_OPTIONS = 10


def ask_number(
    prompt: str,
    minimum: float,
    maximum: float | None = None,
    optional: bool = False,
) -> float | None:
    while True:
        raw = input(prompt).strip()

        if not raw and optional:
            return None

        try:
            number = float(raw)
        except ValueError:
            print("Please enter a valid number.")
            continue

        if not math.isfinite(number) or number < minimum:
            print(f"Enter a finite number >= {minimum}.")
            continue

        if maximum is not None and number > maximum:
            print(f"Enter a number <= {maximum}.")
            continue

        return number


def ask_options() -> list[dict[str, Any]]:
    while True:
        raw = input("How many candidate actions? (0-10): ").strip()
        try:
            count = int(raw)
        except ValueError:
            print("Enter a whole number from 0 to 10.")
            continue

        if 0 <= count <= MAX_OPTIONS:
            break

        print("Enter a whole number from 0 to 10.")

    options = []

    for index in range(count):
        print(f"\n--- Action {index + 1} ---")

        description = input("Describe this action: ").strip()
        while not description:
            description = input("Description is required: ").strip()

        option: dict[str, Any] = {
            "id": f"option-{index + 1}",
            "description": description,
        }

        print("Rate each factor from 1 (low) to 5 (high).")
        for field in RATING_FIELDS:
            option[field] = ask_number(f"  {field} (1-5): ", 1, 5)

        option["cost"] = ask_number(
            "Estimated cost (blank if unknown): ", 0, optional=True
        )
        option["duration_days"] = ask_number(
            "Estimated duration in days (blank if unknown): ",
            0,
            optional=True,
        )

        risks = input("Known risks, separated by commas (optional): ").strip()
        option["risks"] = (
            [risk.strip() for risk in risks.split(",") if risk.strip()]
            if risks
            else []
        )

        options.append(option)

    return options


def run_interactive() -> int:
    print()
    print("=== KRISONA AI AGENT v0.2 ===")
    print("Practical guidance for real-life problems.")
    print()

    problem = input("Describe your problem or goal: ").strip()
    if not problem:
        print("Please describe your problem.")
        return 2

    details = collect_goal_clarifications(problem)
    situation = details["situation"]
    mission = dict(details["mission"])

    advice = generate_solution_advice(
        problem,
        goal=mission.get("goal"),
        daily_capacity_minutes=details["daily_capacity_minutes"],
        deadline=details["deadline"],
        success_criteria=details["success_criteria"],
    )

    timestamp = datetime.now(timezone.utc).isoformat()
    mission_id = mission.get("mission_id") or str(uuid.uuid4())

    mission["mission_id"] = mission_id
    mission["created_at"] = timestamp
    mission["updated_at"] = timestamp
    mission["situation"] = situation
    mission["deadline"] = details["deadline"]
    mission["success_criteria"] = details["success_criteria"]
    mission["status"] = (
        "identified"
        if mission.get("goal") and mission.get("domain") != "other"
        else "clarifying"
    )
    mission["options"] = []
    mission["plan"] = []

    mission.setdefault("context", {})
    mission["context"]["daily_available_minutes"] = (
        details["daily_capacity_minutes"]
    )

    steps = advice.get("action_plan", [])
    first_step = (
        steps[0].get("task", "Review the recommended approach.")
        if steps else "Review the recommended approach."
    )

    result = {
        "status": "advice_ready",
        "mission": mission,
        "advice": advice,
        "decision": None,
        "next_step": first_step,
        "plan": None,
    }

    record = {
        "mission_id": mission_id,
        "created_at": timestamp,
        "situation": situation,
        "options": [],
        "constraints": details["constraints"],
        "goal_intake": {
            "daily_capacity_minutes": details["daily_capacity_minutes"],
            "success_criteria": details["success_criteria"],
            "deadline": details["deadline"],
        },
        "workflow_result": result,
    }

    MissionStore(DB_PATH).save_mission(record)

    print()
    print("=== KRISONA'S GUIDANCE ===")
    print(f"Mission ID: {mission_id}")
    print(f"Problem category: {advice['problem_type']}")
    print(f"Goal: {mission.get('goal') or 'Needs clarification'}")
    print(f"Domain: {mission.get('domain', 'unknown')}")
    print(f"Deadline: {details['deadline'] or 'Not specified'}")

    print()
    print("RECOMMENDED APPROACH")
    print(advice["recommended_approach"])

    print()
    print("POSSIBLE SOLUTIONS")
    for index, option in enumerate(advice.get("options", []), start=1):
        print(f"\n{index}. {option['name']}")
        print(f"   Benefit: {option['benefit']}")
        print(f"   Trade-off: {option['tradeoff']}")
        print(f"   First step: {option['first_step']}")

    print()
    print("ACTION PLAN")
    for step in steps:
        print(f"- {step['when']}: {step['task']}")

    print()
    print("HOW TO MEASURE PROGRESS")
    print(advice["success_measure"])

    print()
    print(advice["review"])
    print()
    print("Your stated constraints have been saved with this mission.")
    print(
        "Note: This initial rule-based advisor does not yet automatically "
        "filter recommendations by budget or maximum duration."
    )
    print(advice["limitations"])
    print(f"\nSaved locally to: {DB_PATH}")

    return 0



def _select_progress_mission(mission_id: str | None = None) -> dict[str, Any]:
    """Use an explicitly selected mission or the most recently updated one."""
    store = MissionStore(DB_PATH)

    if mission_id:
        record = store.get_mission(mission_id)
        if record is None:
            raise KeyError(f"Unknown mission: {mission_id}")
        return record

    records = store.list_missions(limit=100)
    if not records:
        raise ValueError("No saved missions. Run KRISONA first.")

    print("\nRecent missions:")
    for record in records[:10]:
        workflow = record.get("workflow_result", {})
        status = workflow.get("status", "unknown")
        print(
            f"- {record.get('mission_id', 'unknown')} | "
            f"{status} | {record.get('situation', '')[:70]}"
        )

    print("Press Enter to use the most recently updated mission.")
    chosen_id = input("Mission ID (or Enter): ").strip()
    if not chosen_id:
        return records[0]

    selected = store.get_mission(chosen_id)
    if selected is None:
        raise KeyError(f"Unknown mission: {chosen_id}")
    return selected


def record_progress_interactive(mission_id: str | None = None) -> int:
    store = MissionStore(DB_PATH)
    record = _select_progress_mission(mission_id)
    mission_id = record["mission_id"]

    print(f"\nDaily check-in for: {mission_id}")

    while True:
        raw_minutes = input("Practice minutes today (0-1440): ").strip()
        try:
            minutes = int(raw_minutes)
        except ValueError:
            minutes = -1
        if 0 <= minutes <= 1440:
            break
        print("Enter a whole number from 0 to 1440.")

    activity = input("What did you practise? ").strip()
    while not activity:
        print("Please enter a short description of the activity.")
        activity = input("What did you practise? ").strip()

    while True:
        answer = input("Did you complete your planned session? (y/n): ").strip().casefold()
        if answer in {"y", "yes"}:
            completed = True
            break
        if answer in {"n", "no"}:
            completed = False
            break
        print("Enter y or n.")

    difficulty = input("What was difficult? (optional): ").strip() or None

    while True:
        raw_rating = input("How did it feel? Rate 1-5, or Enter to skip: ").strip()
        if not raw_rating:
            rating = None
            break
        try:
            rating = int(raw_rating)
        except ValueError:
            rating = 0
        if 1 <= rating <= 5:
            break
        print("Enter a whole number from 1 to 5, or press Enter to skip.")

    result = store.record_progress_checkin(
        mission_id,
        minutes=minutes,
        activity=activity,
        completed=completed,
        difficulty=difficulty,
        self_rating=rating,
    )

    print("\nCheck-in saved successfully.")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def show_progress(mission_id: str | None = None) -> int:
    record = _select_progress_mission(mission_id)
    report = summarize_progress(MissionStore(DB_PATH), record["mission_id"])
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def show_weekly_review(mission_id: str | None = None) -> int:
    record = _select_progress_mission(mission_id)
    review = create_weekly_review(
        MissionStore(DB_PATH), record["mission_id"]
    )
    print(json.dumps(review, indent=2, ensure_ascii=False))
    return 0



def record_feedback_interactive(
    mission_id: str | None = None,
) -> int:
    """Capture an explicit rating for a saved mission."""
    store = MissionStore(DB_PATH)
    record = _select_progress_mission(mission_id)
    mission_id = record["mission_id"]

    print(f"\nFeedback for mission: {mission_id}")

    while True:
        raw_rating = input("Rate KRISONA's guidance from 1 to 5: ").strip()
        try:
            rating = int(raw_rating)
        except ValueError:
            rating = 0
        if 1 <= rating <= 5:
            break
        print("Enter a whole number from 1 to 5.")

    while True:
        answer = input("Was the guidance helpful? (y/n): ").strip().casefold()
        if answer in {"y", "yes"}:
            helpful = True
            break
        if answer in {"n", "no"}:
            helpful = False
            break
        print("Enter y or n.")

    comments = input("Additional feedback (optional): ").strip()

    feedback = {"rating": rating, "helpful": helpful}
    if comments:
        feedback["comments"] = comments

    feedback_id = store.record_feedback(mission_id, feedback)

    print("\nFeedback saved successfully.")
    print(json.dumps({
        "mission_id": mission_id,
        "feedback_id": feedback_id,
        "rating": rating,
        "helpful": helpful,
    }, indent=2, ensure_ascii=False))
    return 0


def show_feedback_summary(limit: int = 100) -> int:
    """Display aggregate feedback without revealing private comments."""
    report = summarize_feedback(MissionStore(DB_PATH), limit=limit)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def list_missions() -> int:
    store = MissionStore(DB_PATH)
    records = store.list_missions(limit=20)

    if not records:
        print("No saved missions yet.")
        return 0

    print("\n=== SAVED MISSIONS ===")
    for record in records:
        result = record.get("workflow_result", {})
        print(f"\nID: {record.get('mission_id', 'unknown')}")
        print(f"Created: {record.get('created_at', 'unknown')}")
        print(f"Situation: {record.get('situation', '')[:200]}")
        print(f"Status: {result.get('status', 'unknown')}")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="krisona",
        description="KRISONA AI AGENT - local decision-support CLI",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("run", "list", "checkin", "progress", "review", "feedback", "feedback-summary"),
        default="run",
        help="'run' starts a guided session; 'list' shows saved missions",
    )
    parser.add_argument("--mission-id", help="Target a saved mission ID.")
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Maximum number of missions to analyze (1-100).",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            return list_missions()
        if args.command == "checkin":
            return record_progress_interactive(args.mission_id)
        if args.command == "progress":
            return show_progress(args.mission_id)
        if args.command == "review":
            return show_weekly_review(args.mission_id)
        if args.command == "feedback":
            return record_feedback_interactive(args.mission_id)
        if args.command == "feedback-summary":
            return show_feedback_summary(args.limit)
        return run_interactive()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except (ValueError, OSError, EOFError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
