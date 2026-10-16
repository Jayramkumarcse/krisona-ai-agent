"""Tests for the KRISONA goal pattern analyzer."""

import unittest

from krisona_ai.goal_pattern_analyzer import summarize_goal_records


def record(
    domain="Personal Productivity",
    severity="Low",
    outcome="Yes",
    achievement="80",
    planned="20",
    actual="25",
):
    return {
        "Domain": domain,
        "Severity": severity,
        "Goal_Achieved": outcome,
        "Achievement_%": achievement,
        "Planned_Min": planned,
        "Actual_Min": actual,
        "Time_Variance_Min": str(float(actual) - float(planned)),
    }


class GoalPatternAnalyzerTests(unittest.TestCase):
    def test_calculates_overall_and_group_summaries(self):
        rows = [
            record(outcome="Yes", achievement="90"),
            record(outcome="Partial", achievement="60", planned="30", actual="35"),
            record(
                domain="Agriculture",
                severity="High",
                outcome="No",
                achievement="30",
                planned="60",
                actual="55",
            ),
        ]

        result = summarize_goal_records(rows)

        self.assertEqual(result["records_analyzed"], 3)
        self.assertEqual(result["overall"]["outcome_counts"]["Yes"], 1)
        self.assertEqual(
            result["overall"]["mean_achievement_percent"], 60
        )
        self.assertEqual(
            result["by_domain"]["Personal Productivity"]["records"], 2
        )
        self.assertEqual(
            result["by_domain"]["Personal Productivity"]
            ["outcome_share_percent"]["Yes"],
            50,
        )
        self.assertEqual(result["by_severity"]["High"]["records"], 1)

    def test_rejects_out_of_range_achievement(self):
        with self.assertRaisesRegex(ValueError, "between 0 and 100"):
            summarize_goal_records([record(achievement="101")])

    def test_rejects_inconsistent_time_variance(self):
        row = record()
        row["Time_Variance_Min"] = "999"
        with self.assertRaisesRegex(ValueError, "does not equal"):
            summarize_goal_records([row])

    def test_rejects_missing_fields(self):
        row = record()
        del row["Severity"]
        with self.assertRaisesRegex(ValueError, "Missing required value"):
            summarize_goal_records([row])

    def test_rejects_empty_input(self):
        with self.assertRaisesRegex(ValueError, "No data records"):
            summarize_goal_records([])


if __name__ == "__main__":
    unittest.main()
