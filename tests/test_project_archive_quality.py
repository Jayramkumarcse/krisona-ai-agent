"""Tests for project archive validation and percentage handling."""

import csv
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from krisona_ai.project_archive_quality import (
    EXPECTED_PHASES,
    JSONL_FIELDS,
    SUMMARY_FIELDS,
    validate_project_archive,
)


def create_test_archive(path: Path, goal_pct: str = "85") -> Path:
    """Create a small, internally consistent archive for testing."""
    project_id = "KAI-0001"

    with ZipFile(path, "w") as archive:
        documents = []

        for index, phase in enumerate(sorted(EXPECTED_PHASES), start=1):
            record = {
                "doc_id": f"{project_id}-{phase}",
                "project_id": project_id,
                "phase": phase,
                "domain": "personal_productivity",
                "outcome": "achieved",
                "text": f"Test document for {phase}",
            }
            assert set(record) == JSONL_FIELDS
            documents.append(record)
            archive.writestr(
                f"docs/{project_id}-{phase}.md",
                f"# Test document {index}\n",
            )

        archive.writestr(
            "dataset.jsonl",
            "\n".join(json.dumps(item) for item in documents) + "\n",
        )

        summary = {field: "sample" for field in SUMMARY_FIELDS}
        summary.update({
            "project_id": project_id,
            "domain": "personal_productivity",
            "planned_weeks": "2",
            "actual_weeks": "2",
            "achieved_value": "85",
            "goal_achieved_pct": goal_pct,
            "consistency_score": "80",
        })

        with tempfile.TemporaryFile(mode="w+", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=SUMMARY_FIELDS)
            writer.writeheader()
            writer.writerow(summary)
            file.seek(0)
            archive.writestr("projects_summary.csv", file.read())

    return path


class ProjectArchiveQualityTests(unittest.TestCase):
    def test_valid_archive_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = create_test_archive(Path(directory) / "valid.zip")
            report = validate_project_archive(
                path, expected_documents=5, expected_projects=1
            )

        self.assertTrue(report["valid"])
        self.assertTrue(all(report["checks"].values()))

    def test_attainment_above_100_is_flagged_not_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = create_test_archive(
                Path(directory) / "above_100.zip", goal_pct="105.5"
            )
            report = validate_project_archive(
                path, expected_documents=5, expected_projects=1
            )

        self.assertTrue(report["valid"])
        self.assertEqual(report["goal_attainment_above_100"], 1)
        self.assertEqual(report["invalid_percentages"], 0)
        self.assertTrue(report["checks"]["percentages_non_negative"])

    def test_negative_attainment_fails_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = create_test_archive(
                Path(directory) / "negative.zip", goal_pct="-1"
            )
            report = validate_project_archive(
                path, expected_documents=5, expected_projects=1
            )

        self.assertFalse(report["valid"])
        self.assertEqual(report["invalid_percentages"], 1)
        self.assertFalse(report["checks"]["percentages_non_negative"])


if __name__ == "__main__":
    unittest.main()
