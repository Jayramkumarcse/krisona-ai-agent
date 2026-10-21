"""Validate and load evidence-backed solution catalog records.

This module validates metadata and JSON structure only. It does not fetch
URLs or independently establish the reliability of cited evidence.
"""

from __future__ import annotations

import json
import re
from datetime import date
from math import isfinite
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


MAX_CATALOG_BYTES = 2_000_000
MAX_CATALOG_RECORDS = 500

EVIDENCE_TYPES = {
    "official_guidance",
    "systematic_review",
    "peer_reviewed_study",
    "expert_guidance",
    "community_experience",
}

REQUIRED_FIELDS = {
    "solution_id",
    "problem_type",
    "title",
    "description",
    "source_name",
    "source_url",
    "evidence_summary",
    "verified_on",
    "evidence_type",
    "cost",
    "currency",
    "duration_days",
    "safety_rating",
    "limitations",
    "steps",
}

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:[_-][a-z0-9]+)*$")
_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")


def _text(value: Any, field: str, maximum: int) -> str:
    """Validate and normalize a required text field."""
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text.")

    value = value.strip()
    if not value or len(value) > maximum:
        raise ValueError(
            f"{field} must contain 1 to {maximum} characters."
        )

    if any(
        ord(char) < 32 and char not in "\n\t"
        for char in value
    ):
        raise ValueError(f"{field} contains prohibited control characters.")

    return value


def _optional_cost(value: Any) -> float | None:
    """Validate an optional, non-negative cost."""
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("cost must be a finite non-negative number or None.")

    try:
        number = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(
            "cost must be a finite non-negative number or None."
        ) from error

    if not isfinite(number) or number < 0:
        raise ValueError("cost must be a finite non-negative number or None.")

    return number


def _optional_duration(value: Any) -> int | None:
    """Validate an optional duration measured in days."""
    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("duration_days must be a positive integer or None.")

    return value


def _optional_safety_rating(value: Any) -> int | None:
    """Validate an optional human-assessed safety rating."""
    if value is None:
        return None

    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= 5
    ):
        raise ValueError("safety_rating must be an integer from 1 to 5 or None.")

    return value


def _text_list(
    value: Any,
    field: str,
    *,
    minimum: int,
    maximum: int,
    item_maximum: int = 500,
) -> list[str]:
    """Validate a bounded list of text values."""
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(
            f"{field} must be a list containing {minimum} to {maximum} items."
        )

    return [
        _text(item, f"{field}[{index}]", item_maximum)
        for index, item in enumerate(value)
    ]


def validate_solution_record(record: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a normalized catalog record.

    Unknown fields are rejected to prevent silently accepting misspelled
    or unsupported metadata.
    """
    if not isinstance(record, dict):
        raise TypeError("solution record must be a dictionary.")

    missing = REQUIRED_FIELDS - set(record)
    unknown = set(record) - REQUIRED_FIELDS

    if missing:
        raise ValueError(
            f"Missing solution fields: {', '.join(sorted(missing))}."
        )

    if unknown:
        raise ValueError(
            f"Unsupported solution fields: {', '.join(sorted(unknown))}."
        )

    solution_id = _text(record["solution_id"], "solution_id", 80)
    if not _ID_PATTERN.fullmatch(solution_id):
        raise ValueError("solution_id has an invalid format.")

    problem_type = _text(record["problem_type"], "problem_type", 80)
    if not _SLUG_PATTERN.fullmatch(problem_type):
        raise ValueError("problem_type must be a lowercase identifier.")

    title = _text(record["title"], "title", 200)
    description = _text(record["description"], "description", 4000)
    source_name = _text(record["source_name"], "source_name", 200)
    source_url = _text(record["source_url"], "source_url", 2048)
    evidence_summary = _text(
        record["evidence_summary"], "evidence_summary", 2000
    )

    # Validate URL structure without downloading or trusting the resource.
    try:
        parsed_url = urlsplit(source_url)
        hostname = parsed_url.hostname
        # Accessing port also rejects malformed port numbers.
        _ = parsed_url.port
    except ValueError as error:
        raise ValueError("source_url is not a valid HTTPS URL.") from error

    if (
        parsed_url.scheme != "https"
        or not hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
    ):
        raise ValueError(
            "source_url must be an HTTPS URL without embedded credentials."
        )

    verified_on = _text(record["verified_on"], "verified_on", 10)
    try:
        parsed_date = date.fromisoformat(verified_on)
    except ValueError as error:
        raise ValueError("verified_on must use YYYY-MM-DD format.") from error

    if parsed_date.isoformat() != verified_on:
        raise ValueError("verified_on must use YYYY-MM-DD format.")

    evidence_type = _text(record["evidence_type"], "evidence_type", 50)
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(
            f"evidence_type must be one of: {', '.join(sorted(EVIDENCE_TYPES))}."
        )

    cost = _optional_cost(record["cost"])
    currency = record["currency"]

    if currency is not None:
        currency = _text(currency, "currency", 3)
        if not _CURRENCY_PATTERN.fullmatch(currency):
            raise ValueError("currency must be a three-letter uppercase code.")

    if cost is not None and currency is None:
        raise ValueError("currency is required when cost is known.")

    duration_days = _optional_duration(record["duration_days"])
    safety_rating = _optional_safety_rating(record["safety_rating"])

    limitations = _text_list(
        record["limitations"],
        "limitations",
        minimum=0,
        maximum=20,
    )
    steps = _text_list(
        record["steps"],
        "steps",
        minimum=1,
        maximum=20,
    )

    return {
        "solution_id": solution_id,
        "problem_type": problem_type,
        "title": title,
        "description": description,
        "source_name": source_name,
        "source_url": source_url,
        "evidence_summary": evidence_summary,
        "verified_on": verified_on,
        "evidence_type": evidence_type,
        "cost": cost,
        "currency": currency,
        "duration_days": duration_days,
        "safety_rating": safety_rating,
        "limitations": limitations,
        "steps": steps,
    }


def validate_solution_catalog(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Validate catalog records and reject duplicate solution IDs."""
    if not isinstance(records, list):
        raise TypeError("catalog must be a list of solution records.")

    if len(records) > MAX_CATALOG_RECORDS:
        raise ValueError(
            f"Catalog must contain no more than {MAX_CATALOG_RECORDS} records."
        )

    validated: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        try:
            clean = validate_solution_record(record)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid catalog record at index {index}: {error}") from error

        solution_id = clean["solution_id"]
        if solution_id in seen_ids:
            raise ValueError(f"Duplicate solution_id: {solution_id}.")

        seen_ids.add(solution_id)
        validated.append(clean)

    return validated


def load_solution_catalog(
    path: str | Path,
) -> list[dict[str, Any]]:
    """Load a bounded UTF-8 JSON catalog from a local file."""
    if not isinstance(path, (str, Path)) or not str(path).strip():
        raise ValueError("path must be a non-empty file path.")

    catalog_path = Path(path).expanduser()
    if not catalog_path.is_file():
        raise ValueError("Catalog path must identify an existing file.")

    try:
        with catalog_path.open("rb") as file:
            raw = file.read(MAX_CATALOG_BYTES + 1)
    except OSError as error:
        raise ValueError("Could not read the solution catalog.") from error

    if len(raw) > MAX_CATALOG_BYTES:
        raise ValueError(
            f"Catalog file exceeds {MAX_CATALOG_BYTES} bytes."
        )

    try:
        decoded = raw.decode("utf-8")
        records = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Catalog must contain valid UTF-8 JSON.") from error

    return validate_solution_catalog(records)
