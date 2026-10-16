"""Analyze goal and execution patterns in the KRISONA demo workbook."""

from __future__ import annotations

import argparse
import json
import math
import posixpath
import re
import sys
import defusedxml.ElementTree as ET
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile
from typing import Any, Iterable, Iterator


DEFAULT_WORKBOOK = Path("data/demo/krisonaai_50k_demo_dataset.xlsx")

REQUIRED_FIELDS = {
    "Domain",
    "Severity",
    "Goal_Achieved",
    "Achievement_%",
    "Planned_Min",
    "Actual_Min",
    "Time_Variance_Min",
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
        raise ValueError(f"Invalid cell reference: {address}")

    index = 0
    for char in match.group():
        index = index * 26 + ord(char) - ord("A") + 1
    return index - 1


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    kind = cell.attrib.get("t")
    value = cell.find("m:v", NS)

    if kind == "inlineStr":
        return "".join(
            part.text or "" for part in cell.iter(MAIN_NS + "t")
        )
    if value is None:
        return ""
    if kind == "s":
        return shared_strings[int(value.text)]
    return value.text or ""


def _iter_worksheet_rows(path: str | Path) -> Iterator[list[str]]:
    """Stream worksheet rows using only Python's standard library."""
    with ZipFile(path) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise ValueError(f"Corrupt workbook file member: {corrupt}")

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
        sheet_path = (
            target.lstrip("/")
            if target.startswith("/")
            else posixpath.normpath(posixpath.join("xl", target))
        )

        shared_strings = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(
                    part.text or ""
                    for part in entry.iter(MAIN_NS + "t")
                )
                for entry in root.findall("m:si", NS)
            ]

        with archive.open(sheet_path) as stream:
            for _, element in ET.iterparse(stream, events=("end",)):
                if element.tag != MAIN_NS + "row":
                    continue

                cells = {}
                for cell in element.findall("m:c", NS):
                    address = cell.attrib.get("r", "")
                    if address:
                        cells[_column_index(address)] = _cell_text(
                            cell, shared_strings
                        ).strip()

                row = [
                    cells.get(index, "")
                    for index in range(max(cells, default=-1) + 1)
                ]
                element.clear()

                if any(row):
                    yield row


def _parse_number(record: dict[str, Any], field: str) -> float:
    try:
        value = float(record[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric field: {field}") from exc

    if not math.isfinite(value):
        raise ValueError(f"Non-finite numeric field: {field}")

    return value


def _new_group() -> dict[str, Any]:
    return {
        "records": 0,
        "outcomes": Counter(),
        "achievement_sum": 0.0,
        "planned_sum": 0.0,
        "actual_sum": 0.0,
        "variance_sum": 0.0,
    }


def _add_record(
    group: dict[str, Any], record: dict[str, Any]
) -> None:
    achievement = _parse_number(record, "Achievement_%")
    planned = _parse_number(record, "Planned_Min")
    actual = _parse_number(record, "Actual_Min")
    variance = _parse_number(record, "Time_Variance_Min")

    if not 0 <= achievement <= 100:
        raise ValueError("Achievement_% must be between 0 and 100.")
    if planned < 0 or actual < 0:
        raise ValueError("Planned_Min and Actual_Min cannot be negative.")

    if abs((actual - planned) - variance) > 0.01:
        raise ValueError(
            "Time_Variance_Min does not equal Actual_Min - Planned_Min."
        )

    outcome = str(record["Goal_Achieved"]).strip()
    if not outcome:
        raise ValueError("Goal_Achieved cannot be blank.")

    group["records"] += 1
    group["outcomes"][outcome] += 1
    group["achievement_sum"] += achievement
    group["planned_sum"] += planned
    group["actual_sum"] += actual
    group["variance_sum"] += variance


def _finish_group(group: dict[str, Any]) -> dict[str, Any]:
    count = group["records"]
    if count == 0:
        return {"records": 0, "outcome_counts": {}}

    outcomes = dict(sorted(group["outcomes"].items()))
    return {
        "records": count,
        "outcome_counts": outcomes,
        "outcome_share_percent": {
            outcome: round(number * 100 / count, 2)
            for outcome, number in outcomes.items()
        },
        "mean_achievement_percent": round(
            group["achievement_sum"] / count, 2
        ),
        "mean_planned_minutes": round(group["planned_sum"] / count, 2),
        "mean_actual_minutes": round(group["actual_sum"] / count, 2),
        "mean_time_variance_minutes": round(
            group["variance_sum"] / count, 2
        ),
    }


def summarize_goal_records(
    records: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize outcome shares and numeric measures by domain and severity."""
    overall = _new_group()
    by_domain: dict[str, dict[str, Any]] = {}
    by_severity: dict[str, dict[str, Any]] = {}
    record_count = 0

    for record in records:
        record_count += 1

        for field in REQUIRED_FIELDS:
            if field not in record or not str(record[field]).strip():
                raise ValueError(f"Missing required value: {field}")

        domain = str(record["Domain"]).strip()
        severity = str(record["Severity"]).strip()
        if not domain or not severity:
            raise ValueError("Domain and Severity cannot be blank.")

        _add_record(overall, record)

        if domain not in by_domain:
            by_domain[domain] = _new_group()
        _add_record(by_domain[domain], record)

        if severity not in by_severity:
            by_severity[severity] = _new_group()
        _add_record(by_severity[severity], record)

    if record_count == 0:
        raise ValueError("No data records found.")

    return {
        "records_analyzed": record_count,
        "overall": _finish_group(overall),
        "by_domain": {
            name: _finish_group(group)
            for name, group in sorted(by_domain.items())
        },
        "by_severity": {
            name: _finish_group(group)
            for name, group in sorted(by_severity.items())
        },
        "interpretation_note": (
            "Descriptive summaries of demo data only. Associations do not "
            "establish causation, and results do not prove real-world "
            "goal-achievement effectiveness."
        ),
    }


def analyze_goal_workbook(
    path: str | Path = DEFAULT_WORKBOOK,
) -> dict[str, Any]:
    rows = iter(_iter_worksheet_rows(path))
    headers = next(rows, None)

    if not headers:
        raise ValueError("Dataset worksheet is empty.")
    if len(headers) != len(set(headers)):
        raise ValueError("Dataset contains duplicate column names.")

    missing = REQUIRED_FIELDS - set(headers)
    if missing:
        raise ValueError(f"Dataset is missing required fields: {sorted(missing)}")

    def records() -> Iterator[dict[str, str]]:
        for row in rows:
            if len(row) > len(headers) and any(
                value for value in row[len(headers):]
            ):
                raise ValueError("Data row has unexpected extra columns.")

            yield {
                headers[index]: row[index] if index < len(row) else ""
                for index in range(len(headers))
            }

    return summarize_goal_records(records())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Summarize goal outcomes in the KRISONA demo workbook."
    )
    parser.add_argument("--workbook", default=str(DEFAULT_WORKBOOK))
    args = parser.parse_args(argv)

    try:
        result = analyze_goal_workbook(args.workbook)
    except (
        OSError, ValueError, KeyError, BadZipFile, ET.ParseError,
    ) as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
