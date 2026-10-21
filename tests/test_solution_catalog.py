"""Tests for solution catalog validation and JSON loading."""

import json
import tempfile
import unittest
from pathlib import Path

from krisona_ai.solution_catalog import (
    load_solution_catalog,
    validate_solution_catalog,
    validate_solution_record,
)


def sample_record(**overrides):
    """Build a test fixture; its example URL is not validated evidence."""
    record = {
        "solution_id": "test-english-practice",
        "problem_type": "spoken_english",
        "title": "Example speaking practice",
        "description": "A schema-test record, not a real recommendation.",
        "source_name": "Example test source",
        "source_url": "https://example.org/test",
        "evidence_summary": "Placeholder used only to test validation.",
        "verified_on": "2026-10-21",
        "evidence_type": "official_guidance",
        "cost": 0,
        "currency": "INR",
        "duration_days": 7,
        "safety_rating": 4,
        "limitations": ["This record contains placeholder evidence."],
        "steps": ["Use this record for schema testing only."],
    }
    record.update(overrides)
    return record


class SolutionCatalogTests(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        record = validate_solution_record(sample_record())

        self.assertEqual(record["solution_id"], "test-english-practice")
        self.assertEqual(record["problem_type"], "spoken_english")
        self.assertEqual(record["cost"], 0.0)
        self.assertEqual(record["currency"], "INR")

    def test_unknown_cost_duration_and_safety_can_be_explicitly_unknown(self):
        record = validate_solution_record(sample_record(
            cost=None,
            currency=None,
            duration_days=None,
            safety_rating=None,
        ))

        self.assertIsNone(record["cost"])
        self.assertIsNone(record["currency"])
        self.assertIsNone(record["duration_days"])
        self.assertIsNone(record["safety_rating"])

    def test_missing_field_is_rejected(self):
        record = sample_record()
        del record["evidence_summary"]

        with self.assertRaisesRegex(ValueError, "Missing solution fields"):
            validate_solution_record(record)

    def test_unknown_field_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported solution fields"):
            validate_solution_record(sample_record(extra_metadata="unknown"))

    def test_insecure_url_is_rejected(self):
        for url in (
            "http://example.org/resource",
            "javascript:alert(1)",
            "https://user:password@example.org/resource",
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "source_url"):
                    validate_solution_record(sample_record(source_url=url))

    def test_invalid_verification_date_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "verified_on"):
            validate_solution_record(sample_record(verified_on="21-10-2026"))

    def test_invalid_cost_is_rejected(self):
        for cost in (True, -1, float("inf"), float("nan"), "unknown"):
            with self.subTest(cost=cost):
                with self.assertRaises(ValueError):
                    validate_solution_record(sample_record(cost=cost))

    def test_known_cost_requires_currency(self):
        with self.assertRaisesRegex(ValueError, "currency is required"):
            validate_solution_record(sample_record(currency=None))

    def test_invalid_duration_and_safety_are_rejected(self):
        for duration in (True, 0, -1, 1.5):
            with self.subTest(duration=duration):
                with self.assertRaisesRegex(ValueError, "duration_days"):
                    validate_solution_record(
                        sample_record(duration_days=duration)
                    )

        for rating in (True, 0, 6, 3.5):
            with self.subTest(rating=rating):
                with self.assertRaisesRegex(ValueError, "safety_rating"):
                    validate_solution_record(
                        sample_record(safety_rating=rating)
                    )

    def test_unknown_evidence_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "evidence_type"):
            validate_solution_record(
                sample_record(evidence_type="trust_me")
            )

    def test_duplicate_solution_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate solution_id"):
            validate_solution_catalog([
                sample_record(),
                sample_record(),
            ])

    def test_non_list_catalog_is_rejected(self):
        with self.assertRaises(TypeError):
            validate_solution_catalog({"solution": sample_record()})

    def test_loads_valid_json_catalog(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(
                json.dumps([sample_record()]),
                encoding="utf-8",
            )

            catalog = load_solution_catalog(path)

        self.assertEqual(len(catalog), 1)
        self.assertEqual(
            catalog[0]["solution_id"],
            "test-english-practice",
        )

    def test_invalid_json_catalog_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text("{invalid json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
                load_solution_catalog(path)

    def test_missing_catalog_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"

            with self.assertRaisesRegex(ValueError, "existing file"):
                load_solution_catalog(path)


if __name__ == "__main__":
    unittest.main()
