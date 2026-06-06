"""Unit tests for the deterministic workout engine. Run: python3 -m unittest"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "personal-trainer", "scripts"))

import workout_engine as we  # noqa: E402
from exercises import LIBRARY  # noqa: E402
from models import to_kg, from_kg, format_weight  # noqa: E402


class TestUnitConversion(unittest.TestCase):
    def test_round_trip_lbs(self):
        kg = to_kg(135, "lbs")
        self.assertAlmostEqual(kg, 61.23, places=1)
        self.assertEqual(from_kg(kg, "lbs"), 135.0)

    def test_kg_passthrough(self):
        self.assertEqual(to_kg(60, "kg"), 60.0)
        self.assertEqual(from_kg(60, "kg"), 60.0)

    def test_format(self):
        self.assertEqual(format_weight(to_kg(135, "lbs"), "lbs"), "135 lbs")
        self.assertEqual(format_weight(None, "lbs"), "bodyweight")


class TestRecommendFocus(unittest.TestCase):
    def test_first_session_starts_rotation(self):
        self.assertEqual(we.recommend_focus("build_muscle", []), "push")
        self.assertEqual(we.recommend_focus("general", []), "upper")

    def test_rotates_after_last(self):
        hist = [{"status": "completed", "focus": "push"}]
        self.assertEqual(we.recommend_focus("build_muscle", hist), "pull")

    def test_wraps_around(self):
        hist = [{"status": "completed", "focus": "legs"}]
        self.assertEqual(we.recommend_focus("build_muscle", hist), "push")

    def test_ignores_incomplete(self):
        hist = [{"status": "in_progress", "focus": "pull"},
                {"status": "completed", "focus": "push"}]
        self.assertEqual(we.recommend_focus("build_muscle", hist), "pull")


class TestRepScheme(unittest.TestCase):
    def test_build_muscle_compound_vs_accessory(self):
        self.assertEqual(we.rep_scheme("build_muscle", True), (4, 8))
        self.assertEqual(we.rep_scheme("build_muscle", False), (3, 12))

    def test_endurance_high_reps(self):
        self.assertEqual(we.rep_scheme("endurance", False), (3, 20))


class TestProgression(unittest.TestCase):
    def test_first_time_no_weight(self):
        w, note = we.next_target([], True)
        self.assertIsNone(w)
        self.assertIn("First time", note)

    def test_progress_when_hit(self):
        perf = [{"weight_kg": 60.0, "top_reps": 8, "target_reps": 8, "hit": True}]
        w, note = we.next_target(perf, True)
        self.assertEqual(w, 62.5)
        self.assertIn("Up", note)

    def test_accessory_smaller_increment(self):
        perf = [{"weight_kg": 20.0, "top_reps": 12, "target_reps": 12, "hit": True}]
        w, _ = we.next_target(perf, False)
        self.assertEqual(w, 21.25)

    def test_hold_when_missed_once(self):
        perf = [{"weight_kg": 60.0, "top_reps": 6, "target_reps": 8, "hit": False}]
        w, note = we.next_target(perf, True)
        self.assertEqual(w, 60.0)
        self.assertIn("Same weight", note)

    def test_deload_after_two_misses(self):
        perf = [
            {"weight_kg": 60.0, "top_reps": 5, "target_reps": 8, "hit": False},
            {"weight_kg": 60.0, "top_reps": 6, "target_reps": 8, "hit": False},
        ]
        w, note = we.next_target(perf, True)
        self.assertEqual(w, 54.0)
        self.assertIn("Deload", note)


class TestExerciseHistory(unittest.TestCase):
    def test_extracts_top_set(self):
        hist = [{
            "focus": "push", "status": "completed",
            "exercises": [{
                "name": "Barbell Bench Press", "target_reps": 8,
                "sets": [
                    {"reps": 8, "weight_kg": 60.0, "completed": True},
                    {"reps": 8, "weight_kg": 62.5, "completed": True},
                    {"reps": 7, "weight_kg": 62.5, "completed": True},
                ],
            }],
        }]
        perf = we.exercise_history(hist, "Barbell Bench Press")
        self.assertEqual(len(perf), 1)
        self.assertEqual(perf[0]["weight_kg"], 62.5)
        self.assertEqual(perf[0]["top_reps"], 7)        # min reps at top weight
        self.assertFalse(perf[0]["hit"])                 # 7 < 8


class TestBuildWorkout(unittest.TestCase):
    def setUp(self):
        self.profile = {
            "goal": "build_muscle", "location": "gym",
            "equipment": ["barbell", "dumbbells", "machines", "cables"],
            "session_duration": 45, "unit_preference": "lbs",
        }

    def test_builds_requested_count(self):
        w = we.build_workout(self.profile, [], LIBRARY)
        self.assertEqual(w.focus, "push")
        self.assertEqual(len(w.exercises), 5)            # 45 min → 5
        self.assertTrue(all(e.sort_order == i for i, e in enumerate(w.exercises)))

    def test_compounds_lead(self):
        w = we.build_workout(self.profile, [], LIBRARY)
        self.assertTrue(w.exercises[0].target_sets >= 3)
        # First push exercise should be a barbell/compound press.
        self.assertIn("Press", w.exercises[0].name)

    def test_home_bodyweight_only_still_builds(self):
        p = dict(self.profile, location="home", equipment=["bodyweight"])
        w = we.build_workout(p, [], LIBRARY)
        self.assertGreaterEqual(len(w.exercises), 3)
        for e in w.exercises:
            self.assertTrue(any(x.name == e.name for x in LIBRARY))

    def test_uses_history_for_progression(self):
        hist = [{
            "focus": "legs", "status": "completed",   # so next focus = push
            "exercises": [{
                "name": "Barbell Bench Press", "target_reps": 8,
                "sets": [{"reps": 8, "weight_kg": 60.0, "completed": True}],
            }],
        }]
        w = we.build_workout(self.profile, hist, LIBRARY)
        bench = next((e for e in w.exercises if e.name == "Barbell Bench Press"), None)
        self.assertIsNotNone(bench)
        self.assertEqual(bench.target_weight_kg, 62.5)   # progressed +2.5


if __name__ == "__main__":
    unittest.main()
