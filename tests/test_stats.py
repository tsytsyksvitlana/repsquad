import unittest

from backend.errors import NotFound, ValidationError
from backend.services import est_1rm
from tests.helpers import lift, make_app, workout


class Estimate1RM(unittest.TestCase):
    def test_formula(self):
        self.assertEqual(est_1rm(100, 1), 100.0)
        self.assertEqual(est_1rm(100, 5), 116.7)
        self.assertEqual(est_1rm(60, 10), 80.0)
        self.assertEqual(est_1rm(0, 20), 0.0)


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.user, _t = self.app.register("alice", "secret123")
        self.uid = self.user["id"]

    def add(self, date, *exercises, vis="private"):
        return self.app.create_workout(self.uid, workout("t", vis, list(exercises), date))

    def test_records_per_exercise(self):
        self.add("2026-06-01", lift("Жим лежачи", (5, 80), (3, 90)))
        self.add("2026-06-08", lift("жим лежачи", (5, 85)), lift("Підтягування", (10, 0), (12, 0)))
        recs = {r["exercise"]: r for r in self.app.records(self.uid)}
        bench = recs["Жим лежачи"]
        self.assertEqual((bench["max_weight_kg"], bench["max_weight_reps"], bench["max_weight_date"]),
                         (90.0, 3, "2026-06-01"))
        self.assertEqual(bench["best_1rm"], 99.2)       # best 1RM: 85*(1+5/30)
        self.assertEqual(bench["workouts"], 2)          # the exercise name is case-insensitive
        pull = recs["Підтягування"]
        self.assertTrue(pull["bodyweight"])
        self.assertEqual(pull["max_reps"], 12)

    def test_same_weight_prefers_more_reps(self):
        self.add("2026-06-01", lift("Присід", (3, 100), (5, 100)))
        self.assertEqual(self.app.records(self.uid)[0]["max_weight_reps"], 5)

    def test_progress_is_chronological_with_one_point_per_workout(self):
        self.add("2026-06-08", lift("Станова", (5, 120), (3, 130)))
        self.add("2026-06-01", lift("Станова", (5, 100)))
        pts = self.app.progress(self.uid, "  станова ")["points"]
        self.assertEqual([p["date"] for p in pts], ["2026-06-01", "2026-06-08"])
        self.assertEqual(pts[1]["max_weight_kg"], 130.0)
        self.assertEqual(pts[1]["volume_kg"], 5 * 120 + 3 * 130)
        self.assertEqual(pts[1]["best_1rm"], max(est_1rm(120, 5), est_1rm(130, 3)))

    def test_progress_errors(self):
        with self.assertRaises(NotFound):
            self.app.progress(self.uid, "Невідома вправа")
        with self.assertRaises(ValidationError):
            self.app.progress(self.uid, "  ")

    def test_stats_include_private_workouts_of_owner_only(self):
        self.add("2026-06-01", lift("Жим", (5, 100)), vis="private")
        bob, _t = self.app.register("bob", "secret123")
        self.assertEqual(self.app.records(bob["id"]), [])
        with self.assertRaises(NotFound):
            self.app.progress(bob["id"], "Жим")
        self.assertEqual(len(self.app.records(self.uid)), 1)

    def test_exercise_suggestions_put_own_first(self):
        self.add("2026-06-01", lift("Моя вправа", (5, 10)))
        self.add("2026-06-02", lift("Моя вправа", (5, 10)), lift("Жим лежачи", (5, 50)))
        names = self.app.exercise_names(self.uid)
        self.assertEqual(names[:2], ["Моя вправа", "Жим лежачи"])
        self.assertEqual(len([n for n in names if n.casefold() == "жим лежачи"]), 1)


if __name__ == "__main__":
    unittest.main()
