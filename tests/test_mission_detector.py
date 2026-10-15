"""Regression tests for KRISONA AI AGENT Mission Detector."""

import unittest

from krisona_ai.mission_detector import detect_mission, extract_goal


class MissionDetectorTests(unittest.TestCase):

    def test_detects_career_mission(self):
        result = detect_mission(
            "I want to get a job and improve my resume in 30 days."
        )
        self.assertEqual(result["domain"], "career")
        self.assertEqual(result["status"], "identified")
        self.assertIn("get a job", result["goal"])
        self.assertEqual(result["time_horizon"], "in 30 days")

    def test_detects_education_mission(self):
        result = detect_mission(
            "I need to study for my exam and finish the syllabus within 2 weeks."
        )
        self.assertEqual(result["domain"], "education")

    def test_detects_daily_life_mission(self):
        result = detect_mission(
            "My morning routine at home is chaotic and I need to organize chores."
        )
        self.assertEqual(result["domain"], "daily_life")

    def test_detects_productivity_mission(self):
        result = detect_mission(
            "I keep procrastinating and cannot focus; help me schedule my tasks."
        )
        self.assertEqual(result["domain"], "productivity")

    def test_latest_does_not_match_education_test_keyword(self):
        result = detect_mission("I need help planning my latest project.")
        self.assertEqual(result["domain"], "productivity")
        self.assertNotIn("test", result["domain_evidence"]["education"])

    def test_hinglish_goal_and_time_horizon_are_separate(self):
        result = detect_mission("Mujhe 30 din mein job chahiye.")
        self.assertEqual(result["domain"], "career")
        self.assertEqual(result["goal"], "job")
        self.assertEqual(result["time_horizon"], "30 din")

    def test_english_goal_and_time_horizon_are_separate(self):
        result = detect_mission("I want to get a job in 30 days.")
        self.assertEqual(result["goal"], "get a job")
        self.assertEqual(result["time_horizon"], "in 30 days")

    def test_generic_help_request_is_not_a_goal(self):
        self.assertIsNone(extract_goal("I need help with my situation."))

    def test_unclear_situation_requests_clarification(self):
        result = detect_mission("I am not sure what to do next.")
        self.assertEqual(result["domain"], "other")
        self.assertIsNone(result["goal"])
        self.assertEqual(result["status"], "clarifying")
        self.assertGreater(len(result["clarifying_questions"]), 0)

    def test_empty_situation_is_rejected(self):
        with self.assertRaises(ValueError):
            detect_mission("   ")

    def test_non_string_situation_is_rejected(self):
        with self.assertRaises(TypeError):
            detect_mission(None)


if __name__ == "__main__":
    unittest.main()
