"""Integration tests for catalog selection and advisor wiring."""

import json
import tempfile
import unittest
from pathlib import Path

from krisona_ai.solution_advisor import generate_solution_advice
from krisona_ai.solution_catalog import (
    find_solutions,
    load_solution_catalog,
)


CATALOG = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "solution_catalog.json"
)


class SolutionCatalogIntegrationTests(unittest.TestCase):
    def test_all_six_problem_categories_have_resources(self):
        categories = {
            "spoken_english",
            "study_and_exams",
            "career_and_job_search",
            "personal_budgeting",
            "stress_management",
            "focus_and_time",
        }

        records = load_solution_catalog(CATALOG)
        self.assertEqual(len(records), 6)

        found_categories = {
            record["problem_type"]
            for record in records
            if find_solutions(record["problem_type"], path=CATALOG)
        }
        self.assertEqual(found_categories, categories)

    def test_known_budget_violation_excludes_resource(self):
        records = load_solution_catalog(CATALOG)
        english = next(
            record for record in records
            if record["problem_type"] == "spoken_english"
        )
        english["cost"] = 3500
        english["currency"] = "INR"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(
                json.dumps([english]),
                encoding="utf-8",
            )
            results = find_solutions(
                "spoken_english",
                constraints={"max_cost": 3000},
                path=path,
            )

        self.assertEqual(results, [])

    def test_unknown_duration_and_safety_require_verification(self):
        results = find_solutions(
            "spoken_english",
            constraints={
                "max_duration_days": 56,
                "min_safety": 3,
            },
            path=CATALOG,
        )

        self.assertTrue(results)
        assessment = results[0]["catalog_assessment"]

        self.assertEqual(
            assessment["status"],
            "needs_verification",
        )
        self.assertEqual(
            assessment["checks"]["max_duration_days"],
            "unknown",
        )
        self.assertEqual(
            assessment["checks"]["min_safety"],
            "unknown",
        )

    def test_non_inr_cost_is_not_compared_as_inr(self):
        records = load_solution_catalog(CATALOG)
        english = next(
            record for record in records
            if record["problem_type"] == "spoken_english"
        )
        english["cost"] = 10
        english["currency"] = "USD"

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "catalog.json"
            path.write_text(
                json.dumps([english]),
                encoding="utf-8",
            )
            results = find_solutions(
                "spoken_english",
                constraints={"max_cost": 1000},
                path=path,
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["catalog_assessment"]["checks"]["max_cost"],
            "currency_mismatch",
        )

    def test_advisor_includes_matching_catalog_resource(self):
        advice = generate_solution_advice(
            "I want to improve my spoken English",
            daily_capacity_minutes=30,
            constraints={"max_cost": 3000},
        )

        resources = advice["catalog_solutions"]

        self.assertTrue(resources)
        self.assertTrue(
            all(
                item["problem_type"] == "spoken_english"
                for item in resources
            )
        )
        self.assertTrue(
            all(
                item["source_url"].startswith("https://")
                for item in resources
            )
        )


if __name__ == "__main__":
    unittest.main()
