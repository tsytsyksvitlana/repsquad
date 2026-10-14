"""Critical rule (REQ-13): a private workout is visible only to its author."""
import unittest

from backend.errors import Forbidden, NotFound
from backend.privacy import VISIBLE_SQL, can_view
from tests.helpers import make_app, workout


class CanViewRule(unittest.TestCase):
    def test_truth_table(self):
        self.assertTrue(can_view(1, "public", 2))
        self.assertTrue(can_view(1, "public", None))
        self.assertTrue(can_view(1, "private", 1))
        self.assertFalse(can_view(1, "private", 2))
        self.assertFalse(can_view(1, "private", None))

    def test_sql_rule_matches_python_rule(self):
        app, _ = make_app()
        a, _t = app.register("alice", "password1")
        b, _t = app.register("bob", "password1")
        app.create_workout(a["id"], workout("pub", "public"))
        app.create_workout(a["id"], workout("priv", "private"))
        for viewer in (a["id"], b["id"], None):
            rows = app._all(f"SELECT w.id, w.user_id, w.visibility FROM workouts w WHERE {VISIBLE_SQL}", {"viewer": viewer})
            sql_ids = {r["id"] for r in rows}
            py_ids = {r["id"] for r in app._all("SELECT id, user_id, visibility FROM workouts")
                      if can_view(r["user_id"], r["visibility"], viewer)}
            self.assertEqual(sql_ids, py_ids, f"viewer={viewer}")


class PrivacyEverywhere(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.alice, _t = self.app.register("alice", "password1")
        self.bob, _t = self.app.register("bob", "password1")
        self.carol, _t = self.app.register("carol", "password1")
        self.pub, _r = self.app.create_workout(self.alice["id"], workout("Публічне", "public"))
        self.priv, _r = self.app.create_workout(self.alice["id"], workout("Приватне", "private"))
        self.app.follow(self.bob["id"], "alice")   # bob follows alice

    def titles(self, page):
        return [w["title"] for w in page["items"]]

    def test_owner_sees_private(self):
        self.assertEqual(self.app.get_workout(self.priv["id"], self.alice["id"])["title"], "Приватне")
        self.assertEqual(set(self.titles(self.app.user_workouts("alice", self.alice["id"]))), {"Публічне", "Приватне"})

    def test_stranger_gets_404_not_403(self):
        with self.assertRaises(NotFound):
            self.app.get_workout(self.priv["id"], self.carol["id"])

    def test_follower_still_cannot_see_private(self):
        with self.assertRaises(NotFound):
            self.app.get_workout(self.priv["id"], self.bob["id"])

    def test_private_hidden_in_feed_discover_and_profile(self):
        for page in (self.app.feed(self.bob["id"]), self.app.discover(self.bob["id"]),
                     self.app.discover(self.carol["id"]), self.app.user_workouts("alice", self.bob["id"])):
            self.assertEqual(self.titles(page), ["Публічне"])

    def test_profile_counter_counts_only_visible(self):
        self.assertEqual(self.app.get_profile("alice", self.alice["id"])["workouts"], 2)
        self.assertEqual(self.app.get_profile("alice", self.bob["id"])["workouts"], 1)

    def test_visibility_filter_cannot_leak(self):
        page = self.app.user_workouts("alice", self.bob["id"], visibility="private")
        self.assertEqual(page["items"], [])

    def test_no_like_or_comment_on_private(self):
        with self.assertRaises(NotFound):
            self.app.toggle_like(self.priv["id"], self.bob["id"])
        with self.assertRaises(NotFound):
            self.app.add_comment(self.priv["id"], self.bob["id"], "привіт")

    def test_switching_to_private_hides_immediately(self):
        self.assertEqual(self.titles(self.app.feed(self.bob["id"])), ["Публічне"])
        self.app.update_workout(self.pub["id"], self.alice["id"], {"visibility": "private"})
        self.assertEqual(self.app.feed(self.bob["id"])["items"], [])
        with self.assertRaises(NotFound):
            self.app.get_workout(self.pub["id"], self.bob["id"])

    def test_switching_to_public_reveals(self):
        self.app.update_workout(self.priv["id"], self.alice["id"], {"visibility": "public"})
        self.assertEqual(self.app.get_workout(self.priv["id"], self.carol["id"])["title"], "Приватне")

    def test_others_cannot_modify_or_delete_even_public(self):
        with self.assertRaises(Forbidden):
            self.app.update_workout(self.pub["id"], self.bob["id"], {"title": "Хак"})
        with self.assertRaises(Forbidden):
            self.app.delete_workout(self.pub["id"], self.bob["id"])

    def test_others_cannot_modify_private_and_learn_nothing(self):
        with self.assertRaises(NotFound):
            self.app.update_workout(self.priv["id"], self.bob["id"], {"visibility": "public"})
        with self.assertRaises(NotFound):
            self.app.delete_workout(self.priv["id"], self.bob["id"])
        self.assertEqual(self.app.get_workout(self.priv["id"], self.alice["id"])["visibility"], "private")

    def test_comment_delete_on_hidden_workout_is_404(self):
        self.app.add_comment(self.pub["id"], self.bob["id"], "Круто")
        cid = self.app.get_workout(self.pub["id"], self.alice["id"])["comments"][0]["id"]
        self.app.update_workout(self.pub["id"], self.alice["id"], {"visibility": "private"})
        with self.assertRaises(NotFound):
            self.app.delete_comment(cid, self.bob["id"])

    def test_records_are_personal_only(self):
        self.assertEqual(self.app.records(self.bob["id"]), [])
        self.assertEqual(len(self.app.records(self.alice["id"])), 1)


if __name__ == "__main__":
    unittest.main()
