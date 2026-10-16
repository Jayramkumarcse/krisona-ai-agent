"""Tests for the AI assistant usage analyzer."""

import csv
import tempfile
import unittest
from pathlib import Path

from krisona_ai.usage_analyzer import analyze_usage_csv


FIELDS = [
    "timestamp",
    "device",
    "usage_category",
    "prompt_length",
    "session_length_minutes",
    "satisfaction_rating",
    "assistant_model",
    "tokens_used",
]


class UsageAnalyzerTests(unittest.TestCase):
    def create_csv(self, directory: str, rows: list[dict[str, str]]) -> Path:
        path = Path(directory) / "usage.csv"
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_summarizes_overall_and_groups(self):
        data = [
            ["2025-01-01", "Desktop", "Education", "10", "4", "5", "GPT-5", "100"],
            ["2025-01-02", "Mobile", "Education", "20", "6", "3", "GPT-5", "300"],
            ["2025-01-03", "Mobile", "Coding", "30", "8", "4", "Mini", "500"],
        ]
        rows = [dict(zip(FIELDS, row)) for row in data]

        with tempfile.TemporaryDirectory() as directory:
            path = self.create_csv(directory, rows)
            result = analyze_usage_csv(path)

        self.assertEqual(result["records_analyzed"], 3)
        self.assertEqual(result["overall"]["average_session_minutes"], 6)
        self.assertEqual(result["overall"]["average_satisfaction_rating"], 4)
        self.assertEqual(result["overall"]["average_tokens_used"], 300)
        self.assertEqual(result["by_usage_category"]["Education"]["records"], 2)
        self.assertEqual(
            result["by_usage_category"]["Education"]["average_session_minutes"],
            5,
        )
        self.assertEqual(result["by_device"]["Mobile"]["records"], 2)
        self.assertEqual(result["by_assistant_model"]["Mini"]["records"], 1)

    def test_rejects_missing_required_column(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("device,usage_category\nDesktop,Education\n")
            with self.assertRaisesRegex(ValueError, "missing required columns"):
                analyze_usage_csv(path)

    def test_rejects_out_of_range_satisfaction(self):
        row = dict.fromkeys(FIELDS, "test")
        row.update({
            "timestamp": "2025-01-01",
            "device": "Desktop",
            "usage_category": "Education",
            "assistant_model": "GPT-5",
            "prompt_length": "20",
            "session_length_minutes": "5",
            "satisfaction_rating": "6",
            "tokens_used": "100",
        })

        with tempfile.TemporaryDirectory() as directory:
            path = self.create_csv(directory, [row])
            with self.assertRaisesRegex(ValueError, "between 1 and 5"):
                analyze_usage_csv(path)


if __name__ == "__main__":
    unittest.main()
