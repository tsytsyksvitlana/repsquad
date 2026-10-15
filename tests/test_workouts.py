import unittest

from backend.errors import ValidationError
from tests.helpers import lift, make_app, workout


class WorkoutTests(unittest.TestCase):
    def setUp(self):
        self.app, self.clock = make_app()
        self.user, _ = self.app.register("alice", "secret123")
        self.uid = self.user["id"]

    def create(self, **kw):
        return self.app.create_workout(self.uid, workout(**kw))

    def test_new_workout_is_private_by_default(self):
        data = workout()
        del data["visibility"]
        w, _ = self.app.create_workout(self.uid, data)
        self.assertEqual(w["visibility"], "private")

    def test_create_and_read_back(self):
        w, _ = self.app.create_workout(self.uid, workout("Груди", "public", [
            lift("Жим лежачи", (5, 80), (5, 82.5)), lift("Віджимання", (20, 0))]))
        got = self.app.get_workout(w["id"], self.uid)
        self.assertEqual([e["name"] for e in got["exercises"]], ["Жим лежачи", "Віджимання"])
        self.assertEqual(got["exercises"][0]["sets"], [{"reps": 5, "weight_kg": 80.0}, {"reps": 5, "weight_kg": 82.5}])
        self.assertEqual((got["sets_count"], got["volume_kg"]), (3, 5 * 80 + 5 * 82.5))
        self.assertTrue(got["is_mine"])

    def test_validation(self):
        bad = [
            dict(title=""), dict(title="x" * 61), dict(visibility="friends"), dict(date="15.06.2026"),
            dict(date="2030-01-01"), dict(date="1999-12-31"), dict(exercises=[]),
            dict(exercises=[{"name": "", "sets": [{"reps": 5, "weight_kg": 10}]}]),
            dict(exercises=[{"name": "Жим", "sets": []}]),
            dict(exercises=[lift("Жим", (0, 10))]), dict(exercises=[lift("Жим", (101, 10))]),
            dict(exercises=[lift("Жим", (5, -1))]), dict(exercises=[lift("Жим", (5, 1001))]),
            dict(exercises=[lift("Жим", (5.5, 10))]), dict(exercises=[lift("Жим", (True, 10))]),
            dict(exercises=[lift("Жим", *[(5, 10)] * 21)]),
            dict(exercises=[lift(f"В{i}", (5, 10)) for i in range(31)]),
            dict(exercises="жим"),
        ]
        for kw in bad:
            with self.assertRaises(ValidationError, msg=str(kw)[:60]):
                self.create(**kw)
        self.assertEqual(self.app.user_workouts("alice", self.uid)["items"], [])

    def test_boundary_values_accepted(self):
        self.create(exercises=[lift("Планка", (1, 0), (100, 1000))])
        self.create(date="2026-06-16")   # tomorrow is allowed (time zones)

    def test_exercise_names_are_normalized(self):
        w, _ = self.create(exercises=[lift("  Жим   лежачи ", (5, 80))])
        self.assertEqual(w["exercises"][0]["name"], "Жим лежачи")

    def test_update_and_delete(self):
        w, _ = self.create()
        upd = self.app.update_workout(w["id"], self.uid, {"title": "Нова", "notes": "нотатка", "visibility": "public"})
        self.assertEqual((upd["title"], upd["notes"], upd["visibility"]), ("Нова", "нотатка", "public"))
        with self.assertRaises(ValidationError):
            self.app.update_workout(w["id"], self.uid, {"visibility": "secret"})
        self.app.delete_workout(w["id"], self.uid)
        self.assertEqual(self.app.user_workouts("alice", self.uid)["items"], [])
        self.assertEqual(self.app._one("SELECT COUNT(*) AS n FROM sets")["n"], 0)   # cascade delete

    def test_list_is_sorted_newest_first_and_paginated(self):
        for d in ("2026-06-10", "2026-06-12", "2026-06-11"):
            self.create(title=d, date=d)
        page = self.app.user_workouts("alice", self.uid, limit=2)
        self.assertEqual([w["title"] for w in page["items"]], ["2026-06-12", "2026-06-11"])
        self.assertTrue(page["has_more"])
        page2 = self.app.user_workouts("alice", self.uid, limit=2, offset=2)
        self.assertEqual([w["title"] for w in page2["items"]], ["2026-06-10"])
        self.assertFalse(page2["has_more"])
        with self.assertRaises(ValidationError):
            self.app.user_workouts("alice", self.uid, limit="abc")

    def test_owner_visibility_filter(self):
        self.create(title="a", visibility="public")
        self.create(title="b", visibility="private")
        page = self.app.user_workouts("alice", self.uid, visibility="private")
        self.assertEqual([w["title"] for w in page["items"]], ["b"])

    def test_new_personal_record_detected(self):
        _, first = self.create(exercises=[lift("Жим лежачи", (5, 80))])
        self.assertEqual(first, [])   # the first performance is a baseline, not a record
        _, same = self.create(exercises=[lift("жим лежачи", (5, 80))])
        self.assertEqual(same, [])
        _, better = self.create(exercises=[lift("Жим лежачи", (3, 90), (5, 85))])
        self.assertEqual(better, [{"exercise": "Жим лежачи", "weight_kg": 90.0, "reps": 3, "previous_kg": 80.0}])

    def test_records_of_other_users_do_not_count(self):
        bob, _ = self.app.register("bob", "secret123")
        self.app.create_workout(bob["id"], workout(exercises=[lift("Жим лежачи", (5, 200))]))
        self.create(exercises=[lift("Жим лежачи", (5, 80))])
        _, rec = self.create(exercises=[lift("Жим лежачи", (5, 85))])
        self.assertEqual(rec[0]["previous_kg"], 80.0)


if __name__ == "__main__":
    unittest.main()
