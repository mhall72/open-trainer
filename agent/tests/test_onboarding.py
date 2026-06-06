"""Tests for onboarding free-text parsing. Run: python3 -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "personal-trainer", "scripts"))

import onboarding as ob  # noqa: E402


class TestParsing(unittest.TestCase):
    def test_goal(self):
        self.assertEqual(ob.parse_goal("I want to build muscle"), "build_muscle")
        self.assertEqual(ob.parse_goal("lose some fat"), "lose_weight")
        self.assertEqual(ob.parse_goal("just general health"), "general")
        self.assertEqual(ob.parse_goal("run a marathon"), "endurance")
        self.assertIsNone(ob.parse_goal("blah"))

    def test_location(self):
        self.assertEqual(ob.parse_location("at the gym"), "gym")
        self.assertEqual(ob.parse_location("home workouts"), "home")
        self.assertEqual(ob.parse_location("both honestly"), "both")

    def test_personality(self):
        self.assertEqual(ob.parse_personality("hype me up coach"), "motivational")
        self.assertEqual(ob.parse_personality("direct, no fluff"), "nononsense")
        self.assertEqual(ob.parse_personality("explain the science"), "science")

    def test_unit(self):
        self.assertEqual(ob.parse_unit("pounds please"), "lbs")
        self.assertEqual(ob.parse_unit("kg"), "kg")
        self.assertIsNone(ob.parse_unit("dunno"))

    def test_duration(self):
        self.assertEqual(ob.parse_duration("45 min"), 45)
        self.assertEqual(ob.parse_duration("about an hour"), 60)   # nearest of 30/45/60 → 60? "hour" no digits
        self.assertEqual(ob.parse_duration("flexible"), 0)
        self.assertEqual(ob.parse_duration("50 minutes"), 45)      # nearest bucket

    def test_equipment(self):
        eq = ob.parse_equipment("I have a barbell and some dumbbells")
        self.assertIn("barbell", eq)
        self.assertIn("dumbbells", eq)
        self.assertIn("bodyweight", eq)               # always added
        self.assertEqual(ob.parse_equipment("nothing, just me"), ["bodyweight"])

    def test_next_step_progression(self):
        self.assertEqual(ob.next_step({}), "goal")
        p = {"goal": "build_muscle", "location": "gym", "equipment": ["barbell"],
             "session_duration": 45, "personality": "motivational", "unit_preference": "lbs"}
        self.assertIsNone(ob.next_step(p))
        p2 = dict(p); p2.pop("personality")
        self.assertEqual(ob.next_step(p2), "personality")

    def test_summary(self):
        p = {"goal": "build_muscle", "location": "gym", "equipment": ["barbell", "dumbbells"],
             "session_duration": 45, "personality": "motivational", "unit_preference": "lbs"}
        s = ob.summary(p)
        self.assertIn("Build Muscle", s)
        self.assertIn("Gym", s)
        self.assertIn("Motivational", s)


if __name__ == "__main__":
    unittest.main()
