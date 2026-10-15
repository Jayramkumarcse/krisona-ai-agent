"""Repeatable offline evaluation for the supplied-option decision engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .decision_engine import evaluate_options

MAX_CASES = 100
VALID_STATUSES = {"recommended", "clarifying", "no_feasible_option"}


def evaluate_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare actual engine behavior against explicit expected outcomes."""
    if not isinstance(cases, list):
        raise TypeError("cases must be a list.")
    if not cases or len(cases) > MAX_CASES:
        raise ValueError(f"cases must contain 1 to {MAX_CASES} entries.")

    seen_ids: set[str] = set()
    results = []

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case {index} must be an object.")

        allowed = {
            "id", "description", "expected_status",
            "expected_option_id", "constraints", "options",
        }
        if set(case) - allowed:
            raise ValueError(f"Case {index} has unsupported fields.")

        case_id = case.get("id")
        if (
            not isinstance(case_id, str)
            or not case_id
            or len(case_id) > 80
            or any(ord(char) < 32 or ord(char) == 127 for char in case_id)
        ):
            raise ValueError(f"Case {index} has an invalid id.")
        if case_id in seen_ids:
            raise ValueError(f"Duplicate case id: {case_id}.")
        seen_ids.add(case_id)

        expected_status = case.get("expected_status")
        if expected_status not in VALID_STATUSES:
            raise ValueError(f"{case_id} has an invalid expected_status.")

        expected_id = case.get("expected_option_id")
        if expected_id is not None and (
            not isinstance(expected_id, str) or not expected_id
        ):
            raise ValueError(f"{case_id} has an invalid expected_option_id.")

        actual = evaluate_options(
            case.get("options"),
            case.get("constraints", {}),
        )

        actual_id = actual["selected_option_id"]
        status_match = actual["status"] == expected_status
        selection_match = actual_id == expected_id

        chosen_status = None
        if actual_id is not None:
            chosen = next(
                item for item in actual["evaluated_options"]
                if item["id"] == actual_id
            )
            chosen_status = chosen["status"]

        results.append({
            "id": case_id,
            "expected_status": expected_status,
            "actual_status": actual["status"],
            "expected_option_id": expected_id,
            "actual_option_id": actual_id,
            "status_match": status_match,
            "selection_match": selection_match,
            "selected_option_is_eligible": (
                chosen_status == "eligible" if actual_id is not None else None
            ),
            "passed": status_match and selection_match,
        })

    count = len(results)
    passed = sum(item["passed"] for item in results)
    status_matches = sum(item["status_match"] for item in results)
    selection_matches = sum(item["selection_match"] for item in results)
    recommendations = [
        item for item in results if item["actual_option_id"] is not None
    ]
    eligible_selections = sum(
        item["selected_option_is_eligible"] is True
        for item in recommendations
    )

    return {
        "suite": "decision_engine_v0.1",
        "case_count": count,
        "passed_cases": passed,
        "failed_cases": count - passed,
        "case_pass_rate_percent": round(passed / count * 100, 1),
        "status_accuracy_percent": round(status_matches / count * 100, 1),
        "selection_accuracy_percent": round(
            selection_matches / count * 100, 1
        ),
        "recommendation_count": len(recommendations),
        "eligible_selection_count": eligible_selections,
        "results": results,
        "interpretation": (
            "This small curated suite checks specified behaviors only. "
            "It does not establish real-world decision quality or "
            "generalization to unseen situations."
        ),
    }


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    dataset_path = project_root / "data" / "decision_evaluation_cases.json"

    try:
        cases = json.loads(dataset_path.read_text(encoding="utf-8"))
        report = evaluate_cases(cases)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise SystemExit(f"Evaluation failed: {exc}") from exc

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if report["failed_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
