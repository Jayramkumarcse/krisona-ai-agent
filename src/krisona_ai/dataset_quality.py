"""Validate the structure and basic quality of KRISONA's 50K workbook."""

from __future__ import annotations

import argparse
import json
import math
import posixpath
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator
from zipfile import BadZipFile, ZipFile
import defusedxml.ElementTree as ET


DEFAULT_WORKBOOK = Path("data/demo/krisonaai_50k_demo_dataset.xlsx")
EXPECTED_ROWS = 50_000

EXPECTED_HEADERS = [
    "Record_ID", "Date", "Day", "Domain", "Who (Persona)",
    "Where (Location)", "When (Time Slot)", "What: Daily Little Goal",
    "What: Problem Faced", "Why: Root Cause", "Context Signals",
    "Severity", "How: Best Solution Process", "Best Decision",
    "Should Do", "Should NOT Do", "Critical Situation Guide",
    "Appropriate Solution Applied", "Whom to Involve", "Planned_Min",
    "Actual_Min", "Time_Variance_Min", "Goal_Achieved", "Achievement_%",
    "Consistency_Streak_Days", "Lesson Learned",
]

NUMERIC_FIELDS = (
    "Planned_Min",
    "Actual_Min",
    "Time_Variance_Min",
    "Achievement_%",
    "Consistency_Streak_Days",
)

NON_NEGATIVE_FIELDS = {
    "Planned_Min", "Actual_Min", "Consistency_Streak_Days",
}

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_ID = (
    "{http://schemas.openxmlformats.org/officeDocument/2006/"
    "relationships}id"
)


def _column_index(address: str) -> int:
    match = re.match(r"[A-Z]+", address)
    if not match:
        raise ValueError(f"Invalid spreadsheet cell reference: {address}")

    index = 0
    for char in match.group():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find("m:v", NS)

    if kind == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter(MAIN_NS + "t")
        )
    if value is None:
        return ""
    if kind == "s":
        return shared_strings[int(value.text)]
    return value.text or ""


def _iter_dataset_rows(path: Path) -> Iterator[list[str]]:
    """Stream nonempty rows from the Dataset worksheet using stdlib XML."""
    with ZipFile(path) as archive:
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise ValueError(f"Corrupt workbook member: {corrupt_member}")

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(
            archive.read("xl/_rels/workbook.xml.rels")
        )
        rels = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships
        }

        sheet = next(
            (
                item
                for item in workbook.findall("m:sheets/m:sheet", NS)
                if item.attrib["name"] == "Dataset"
            ),
            None,
        )
        if sheet is None:
            raise ValueError("Workbook has no 'Dataset' worksheet.")

        target = rels[sheet.attrib[REL_ID]]
        if target.startswith("/"):
            sheet_path = target.lstrip("/")
        else:
            sheet_path = posixpath.normpath(
                posixpath.join("xl", target)
            )

        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(
                    node.text or "" for node in item.iter(MAIN_NS + "t")
                )
                for item in root.findall("m:si", NS)
            ]

        with archive.open(sheet_path) as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if element.tag != MAIN_NS + "row":
                    continue

                cells: dict[int, str] = {}
                for cell in element.findall("m:c", NS):
                    address = cell.attrib.get("r", "")
                    if address:
                        cells[_column_index(address)] = _cell_text(
                            cell, shared_strings
                        ).strip()

                values = [
                    cells.get(index, "")
                    for index in range(max(cells, default=-1) + 1)
                ]
                element.clear()

                if any(values):
                    yield values


def analyze_records(
    headers: list[str],
    records: Iterable[dict[str, Any]],
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    """Validate records and return a JSON-serializable quality profile."""
    schema_matches = headers == EXPECTED_HEADERS
    duplicate_headers = len(headers) != len(set(headers))

    missing = Counter()
    categories = {
        field: Counter()
        for field in (
            "Domain", "Severity", "Goal_Achieved", "Day",
            "Who (Persona)",
        )
    }
    numeric = {
        field: {
            "count": 0,
            "invalid": 0,
            "out_of_range": 0,
            "min": None,
            "max": None,
        }
        for field in NUMERIC_FIELDS
    }

    seen_ids: set[str] = set()
    duplicate_ids = 0
    row_count = 0
    variance_mismatches = 0

    for record in records:
        row_count += 1

        for field in EXPECTED_HEADERS:
            value = record.get(field, "")
            if value is None or not str(value).strip():
                missing[field] += 1

        record_id = str(record.get("Record_ID", "")).strip()
        if record_id:
            if record_id in seen_ids:
                duplicate_ids += 1
            seen_ids.add(record_id)

        for field, counts in categories.items():
            value = str(record.get(field, "")).strip()
            if value:
                counts[value] += 1

        parsed: dict[str, float] = {}
        for field in NUMERIC_FIELDS:
            raw = record.get(field, "")
            if raw is None or not str(raw).strip():
                continue

            try:
                number = float(raw)
                if not math.isfinite(number):
                    raise ValueError
            except (ValueError, TypeError):
                numeric[field]["invalid"] += 1
                continue

            stat = numeric[field]
            stat["count"] += 1
            stat["min"] = (
                number if stat["min"] is None
                else min(stat["min"], number)
            )
            stat["max"] = (
                number if stat["max"] is None
                else max(stat["max"], number)
            )
            parsed[field] = number

            if field in NON_NEGATIVE_FIELDS and number < 0:
                stat["out_of_range"] += 1
            if field == "Achievement_%" and not 0 <= number <= 100:
                stat["out_of_range"] += 1

        time_fields = (
            "Planned_Min", "Actual_Min", "Time_Variance_Min"
        )
        if all(field in parsed for field in time_fields):
            expected_variance = (
                parsed["Actual_Min"] - parsed["Planned_Min"]
            )
            if abs(expected_variance - parsed["Time_Variance_Min"]) > 0.01:
                variance_mismatches += 1

    missing_by_column = {
        field: missing.get(field, 0) for field in EXPECTED_HEADERS
    }
    numeric_valid = all(
        stat["count"] == row_count
        and stat["invalid"] == 0
        and stat["out_of_range"] == 0
        for stat in numeric.values()
    )

    checks = {
        "schema_matches_expected": schema_matches and not duplicate_headers,
        "expected_record_count": row_count == expected_rows,
        "no_missing_values": sum(missing.values()) == 0,
        "unique_nonblank_record_ids": (
            duplicate_ids == 0 and len(seen_ids) == row_count
        ),
        "numeric_fields_valid": numeric_valid,
        "time_variance_consistent": variance_mismatches == 0,
    }

    return {
        "records_analyzed": row_count,
        "column_count": len(headers),
        "schema_matches_expected": schema_matches,
        "duplicate_header_names": duplicate_headers,
        "unique_nonblank_record_ids": len(seen_ids),
        "duplicate_record_id_occurrences": duplicate_ids,
        "missing_values_by_column": missing_by_column,
        "category_distributions": {
            field: dict(sorted(counts.items()))
            for field, counts in categories.items()
        },
        "numeric_statistics": numeric,
        "time_variance_mismatches": variance_mismatches,
        "checks": checks,
        "valid": all(checks.values()),
    }


def validate_workbook(
    path: str | Path = DEFAULT_WORKBOOK,
    expected_rows: int = EXPECTED_ROWS,
) -> dict[str, Any]:
    workbook_path = Path(path)
    row_iterator = iter(_iter_dataset_rows(workbook_path))
    header_row = next(row_iterator, None)

    if not header_row:
        raise ValueError("Dataset worksheet is empty.")

    def records():
        for row in row_iterator:
            if len(row) > len(header_row) and any(
                value for value in row[len(header_row):]
            ):
                raise ValueError("A data row has unexpected extra columns.")

            yield {
                header_row[index]: row[index] if index < len(row) else ""
                for index in range(len(header_row))
                if header_row[index]
            }

    return analyze_records(header_row, records(), expected_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the KRISONA 50K demo workbook."
    )
    parser.add_argument(
        "--workbook",
        default=str(DEFAULT_WORKBOOK),
        help="Path to the XLSX workbook.",
    )
    parser.add_argument(
        "--expected-rows",
        type=int,
        default=EXPECTED_ROWS,
        help="Expected number of data rows (default: 50000).",
    )
    args = parser.parse_args(argv)

    if args.expected_rows < 0:
        parser.error("--expected-rows cannot be negative")

    try:
        report = validate_workbook(args.workbook, args.expected_rows)
    except (
        OSError, ValueError, KeyError, StopIteration,
        BadZipFile, ET.ParseError,
    ) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
