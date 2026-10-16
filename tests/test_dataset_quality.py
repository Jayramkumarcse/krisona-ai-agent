"""Tests for the KRISONA workbook quality analyzer."""

import unittest

from krisona_ai.dataset_quality import (
    EXPECTED_HEADERS,
    analyze_records,
)


def make_record(record_id="KAI-1"):
    row = {header: "sample" for header in EXPECTED_HEADERS}
    row.update({
        "Record_ID": record_id,
        "Date": "46047",
        "Day": "Sun",
        "Domain": "Personal Productivity",
        "Severity": "Low",
        "Goal_Achieved": "Yes",
        "Planned_Min": "20",
        "Actual_Min": "25",
        "Time_Variance_Min": "5",
        "Achievement_%": "80",
        "Consistency_Streak_Days": "3",
    })
    return row


class DatasetQualityTests(unittest.TestCase):
    def test_valid_records_pass(self):
        report = analyze_records(
            EXPECTED_HEADERS,
            [make_record("KAI-1"), make_record("KAI-2")],
            expected_rows=2,
        )
        self.assertTrue(report["valid"])
        self.assertEqual(report["records_analyzed"], 2)
        self.assertEqual(report["duplicate_record_id_occurrences"], 0)

    def test_duplicate_ids_fail(self):
        report = analyze_records(
            EXPECTED_HEADERS,
            [make_record("KAI-1"), make_record("KAI-1")],
            expected_rows=2,
        )
        self.assertFalse(report["checks"]["unique_nonblank_record_ids"])

    def test_missing_value_fails(self):
        row = make_record()
        row["Best Decision"] = ""
        report = analyze_records(
            EXPECTED_HEADERS, [row], expected_rows=1
        )
        self.assertFalse(report["checks"]["no_missing_values"])

    def test_invalid_numeric_value_fails(self):
        row = make_record()
        row["Actual_Min"] = "unknown"
        report = analyze_records(
            EXPECTED_HEADERS, [row], expected_rows=1
        )
        self.assertFalse(report["checks"]["numeric_fields_valid"])

    def test_achievement_over_100_fails(self):
        row = make_record()
        row["Achievement_%"] = "101"
        report = analyze_records(
            EXPECTED_HEADERS, [row], expected_rows=1
        )
        self.assertFalse(report["checks"]["numeric_fields_valid"])

    def test_time_variance_mismatch_fails(self):
        row = make_record()
        row["Time_Variance_Min"] = "10"
        report = analyze_records(
            EXPECTED_HEADERS, [row], expected_rows=1
        )
        self.assertFalse(report["checks"]["time_variance_consistent"])

    def test_wrong_schema_fails(self):
        headers = EXPECTED_HEADERS[:-1]
        row = make_record()
        report = analyze_records(headers, [row], expected_rows=1)
        self.assertFalse(report["checks"]["schema_matches_expected"])

    def test_wrong_row_count_fails(self):
        report = analyze_records(
            EXPECTED_HEADERS, [make_record()], expected_rows=2
        )
        self.assertFalse(report["checks"]["expected_record_count"])


if __name__ == "__main__":
    unittest.main()
