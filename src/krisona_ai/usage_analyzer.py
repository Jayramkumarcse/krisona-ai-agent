"""Analyze AI assistant usage patterns from a local CSV file."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_CSV = Path("data/raw/daily_ai_assistant_usage_behavior.csv")

REQUIRED_FIELDS = {
    "timestamp",
    "device",
    "usage_category",
    "prompt_length",
    "session_length_minutes",
    "satisfaction_rating",
    "assistant_model",
    "tokens_used",
}

NUMERIC_FIELDS = (
    "prompt_length",
    "session_length_minutes",
    "satisfaction_rating",
    "tokens_used",
)


def _number(value: str, field: str, line: int) -> float:
    """Parse and validate a finite, non-negative numeric field."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid number in '{field}' on CSV line {line}."
        ) from exc

    if not math.isfinite(number) or number < 0:
        raise ValueError(
            f"Expected a finite, non-negative '{field}' on line {line}."
        )

    if field == "satisfaction_rating" and not 1 <= number <= 5:
        raise ValueError(
            f"'satisfaction_rating' must be between 1 and 5 on line {line}."
        )

    return number


def _summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return descriptive statistics without inferring causation."""
    return {
        "records": len(rows),
        "average_prompt_length": round(
            statistics.mean(row["prompt_length"] for row in rows), 2
        ),
        "average_session_minutes": round(
            statistics.mean(row["session_length_minutes"] for row in rows), 2
        ),
        "median_session_minutes": round(
            statistics.median(row["session_length_minutes"] for row in rows), 2
        ),
        "average_satisfaction_rating": round(
            statistics.mean(row["satisfaction_rating"] for row in rows), 2
        ),
        "average_tokens_used": round(
            statistics.mean(row["tokens_used"] for row in rows), 2
        ),
    }


def analyze_usage_csv(path: str | Path = DEFAULT_CSV) -> dict[str, Any]:
    """Validate the CSV and summarize usage by category, device, and model."""
    csv_path = Path(path)
    required = REQUIRED_FIELDS

    with csv_path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no header row.")

        missing = sorted(required - set(reader.fieldnames))
        if missing:
            raise ValueError(f"CSV is missing required columns: {missing}")

        rows: list[dict[str, Any]] = []

        for line, raw in enumerate(reader, start=2):
            if None in raw:
                raise ValueError(f"Unexpected extra columns on CSV line {line}.")

            record: dict[str, Any] = {}

            for field in ("device", "usage_category", "assistant_model"):
                value = (raw.get(field) or "").strip()
                if not value:
                    raise ValueError(
                        f"Missing '{field}' value on CSV line {line}."
                    )
                record[field] = value

            for field in NUMERIC_FIELDS:
                value = (raw.get(field) or "").strip()
                if not value:
                    raise ValueError(
                        f"Missing '{field}' value on CSV line {line}."
                    )
                record[field] = _number(value, field, line)

            if raw.get(None) is not None:
                raise ValueError(f"Malformed CSV row on line {line}.")

            rows.append(record)

    if not rows:
        raise ValueError("CSV contains no data records.")

    def grouped_summary(field: str) -> dict[str, Any]:
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            groups[row[field]].append(row)

        return {
            key: _summarize(groups[key])
            for key in sorted(groups, key=str.casefold)
        }

    return {
        "source": str(csv_path),
        "records_analyzed": len(rows),
        "overall": _summarize(rows),
        "by_usage_category": grouped_summary("usage_category"),
        "by_device": grouped_summary("device"),
        "by_assistant_model": grouped_summary("assistant_model"),
        "interpretation_note": (
            "These are descriptive statistics. They do not establish "
            "causation or prove goal-achievement effectiveness."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize KRISONA's AI assistant usage dataset."
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_CSV),
        help="Path to the usage CSV.",
    )
    args = parser.parse_args(argv)

    try:
        result = analyze_usage_csv(args.csv)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
