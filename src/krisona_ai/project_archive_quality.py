"""Validate the KRISONA project-document archive."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import sys
from collections import Counter
from pathlib import Path
from zipfile import BadZipFile, ZipFile

DEFAULT_ARCHIVE = Path("data/raw/krisonaai_5000_docs.zip")

JSONL_FIELDS = {
    "doc_id", "project_id", "phase", "domain", "outcome", "text"
}

SUMMARY_FIELDS = [
    "project_id", "domain", "scale", "problem", "user", "needs",
    "datasets", "kpi_name", "baseline", "target", "sol_baseline",
    "sol_better", "sol_best", "chosen", "planned_weeks",
    "outcome", "actual_weeks", "achieved_value",
    "goal_achieved_pct", "consistency_score",
]

NUMERIC_FIELDS = (
    "planned_weeks", "actual_weeks", "achieved_value",
    "goal_achieved_pct", "consistency_score",
)

EXPECTED_PHASES = {
    "P1_discovery",
    "P2_goal_scope",
    "P3_solution",
    "P4_build_pilot",
    "P5_review",
}


def validate_project_archive(
    path: str | Path = DEFAULT_ARCHIVE,
    expected_documents: int = 5000,
    expected_projects: int = 1000,
) -> dict:
    """Validate archive structure and consistency between its data files."""
    report = {
        "archive": str(path),
        "jsonl_records": 0,
        "summary_rows": 0,
        "markdown_documents": 0,
        "duplicate_doc_ids": 0,
        "duplicate_project_ids": 0,
        "jsonl_missing_values": 0,
        "summary_missing_values": 0,
        "invalid_numeric_values": 0,
        "invalid_percentages": 0,
        "goal_attainment_above_100": 0,
        "interpretation_note": (
            "Non-negative goal attainment values above 100 are flagged "
            "for review, not automatically rejected. Verify the metric "
            "definition and KPI direction before downstream use."
        ),
        "malformed_json_lines": 0,
        "schema_mismatches": 0,
        "projects_with_wrong_phases": 0,
        "project_ids_missing_from_summary": 0,
        "summary_projects_without_documents": 0,
        "checks": {},
    }

    with ZipFile(path) as archive:
        corrupt = archive.testzip()
        names = set(archive.namelist())

        report["markdown_documents"] = sum(
            name.startswith("docs/") and name.endswith(".md")
            for name in names
        )

        required_files = {"dataset.jsonl", "projects_summary.csv"}
        files_present = required_files.issubset(names)
        if not files_present:
            raise ValueError(
                f"Archive is missing required files: "
                f"{sorted(required_files - names)}"
            )

        docs = []
        with archive.open("dataset.jsonl") as binary:
            stream = io.TextIOWrapper(binary, encoding="utf-8-sig")
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    report["malformed_json_lines"] += 1
                    continue

                if not isinstance(record, dict):
                    report["schema_mismatches"] += 1
                    continue

                report["jsonl_records"] += 1
                if set(record) != JSONL_FIELDS:
                    report["schema_mismatches"] += 1

                if any(
                    not isinstance(record.get(field), str)
                    or not record[field].strip()
                    for field in JSONL_FIELDS
                ):
                    report["jsonl_missing_values"] += 1

                docs.append(record)

        summary_rows = []
        with archive.open("projects_summary.csv") as binary:
            stream = io.TextIOWrapper(
                binary, encoding="utf-8-sig", newline=""
            )
            reader = csv.DictReader(stream)
            headers = reader.fieldnames or []
            report["summary_schema_matches"] = headers == SUMMARY_FIELDS

            for row in reader:
                report["summary_rows"] += 1
                summary_rows.append(row)

                for field in SUMMARY_FIELDS:
                    value = row.get(field)
                    if value is None or not value.strip():
                        report["summary_missing_values"] += 1

                for field in NUMERIC_FIELDS:
                    raw = (row.get(field) or "").strip()
                    try:
                        number = float(raw)
                        if not math.isfinite(number):
                            raise ValueError
                    except ValueError:
                        report["invalid_numeric_values"] += 1
                        continue

                    if field in {"planned_weeks", "actual_weeks"}:
                        if number < 0:
                            report["invalid_numeric_values"] += 1
                    if field == "goal_achieved_pct":
                        if number < 0:
                            report["invalid_percentages"] += 1
                        elif number > 100:
                            report["goal_attainment_above_100"] += 1

    doc_ids = [r.get("doc_id") for r in docs if r.get("doc_id")]
    summary_ids = [
        r.get("project_id", "").strip()
        for r in summary_rows
        if r.get("project_id", "").strip()
    ]
    project_phases: dict[str, set[str]] = {}
    doc_project_ids = set()

    for record in docs:
        project_id = record.get("project_id")
        phase = record.get("phase")
        if isinstance(project_id, str) and project_id.strip():
            doc_project_ids.add(project_id)
            project_phases.setdefault(project_id, set())
            if isinstance(phase, str):
                project_phases[project_id].add(phase)

    report["duplicate_doc_ids"] = len(doc_ids) - len(set(doc_ids))
    report["duplicate_project_ids"] = (
        len(summary_ids) - len(set(summary_ids))
    )
    summary_id_set = set(summary_ids)

    report["projects_with_wrong_phases"] = sum(
        phases != EXPECTED_PHASES
        for phases in project_phases.values()
    )
    report["project_ids_missing_from_summary"] = len(
        doc_project_ids - summary_id_set
    )
    report["summary_projects_without_documents"] = len(
        summary_id_set - doc_project_ids
    )

    report["checks"] = {
        "zip_integrity": corrupt is None,
        "required_files_present": files_present,
        "expected_jsonl_record_count": (
            report["jsonl_records"] == expected_documents
        ),
        "expected_markdown_document_count": (
            report["markdown_documents"] == expected_documents
        ),
        "expected_summary_row_count": (
            report["summary_rows"] == expected_projects
        ),
        "jsonl_schema_consistent": (
            report["schema_mismatches"] == 0
            and report["malformed_json_lines"] == 0
        ),
        "summary_schema_matches_expected": report["summary_schema_matches"],
        "no_missing_values": (
            report["jsonl_missing_values"] == 0
            and report["summary_missing_values"] == 0
        ),
        "unique_document_ids": report["duplicate_doc_ids"] == 0
        and len(doc_ids) == report["jsonl_records"],
        "unique_project_ids": report["duplicate_project_ids"] == 0
        and len(summary_ids) == report["summary_rows"],
        "numeric_fields_valid": (
            report["invalid_numeric_values"] == 0
        ),
        "percentages_non_negative": report["invalid_percentages"] == 0,
        "five_expected_phases_per_project": (
            report["projects_with_wrong_phases"] == 0
        ),
        "project_ids_match_across_files": (
            report["project_ids_missing_from_summary"] == 0
            and report["summary_projects_without_documents"] == 0
        ),
    }
    report["valid"] = all(report["checks"].values())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate KRISONA's 5,000-document project archive."
    )
    parser.add_argument("--archive", default=str(DEFAULT_ARCHIVE))
    parser.add_argument("--expected-documents", type=int, default=5000)
    parser.add_argument("--expected-projects", type=int, default=1000)
    args = parser.parse_args(argv)

    if args.expected_documents < 0 or args.expected_projects < 0:
        parser.error("Expected counts cannot be negative.")

    try:
        result = validate_project_archive(
            args.archive,
            args.expected_documents,
            args.expected_projects,
        )
    except (
        OSError, ValueError, BadZipFile, csv.Error,
        KeyError, TypeError,
    ) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
