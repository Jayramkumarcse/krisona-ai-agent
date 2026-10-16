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
from .mission_store import MissionStore
from .mission_workflow import run_mission_workflow


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
    print("\n=== KRISONA AI AGENT v0.1 ===")
    print("Decision support, with user-reviewed inputs.\n")

    situation = input("Describe your goal or situation: ").strip()
    if not situation:
        print("Please enter a situation.")
        return 2

    options = ask_options()

    result = run_mission_workflow(
        situation=situation,
        options=options,
        constraints={},
    )

    mission_id = result.get("mission", {}).get("mission_id")
    if not mission_id:
        mission_id = f"mission-{uuid.uuid4().hex}"

    record = {
        "mission_id": mission_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "situation": situation,
        "options": options,
        "constraints": {},
        "workflow_result": result,
    }

    store = MissionStore(DB_PATH)
    store.save_mission(record)

    print("\n=== RESULT ===")
    print(f"Mission ID: {mission_id}")
    print(f"Saved locally to: {DB_PATH}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
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
        choices=("run", "list"),
        default="run",
        help="'run' starts a guided session; 'list' shows saved missions",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "list":
            return list_missions()
        return run_interactive()
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
    except (ValueError, OSError, EOFError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
