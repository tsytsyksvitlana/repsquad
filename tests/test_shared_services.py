import unittest

from backend.db import connect
from backend.errors import Forbidden, NotFound
from tests.helpers import make_app, workout


class SharedHelperTests(unittest.TestCase):
    """Workouts and posts share one implementation of likes, comments, visibility and ownership."""

    def setUp(self):
        self.app, _ = make_app()
        self.alice = self.app.register("alice", "secret123")[0]["id"]
        self.bob = self.app.register("bob", "secret123")[0]["id"]
        self.carol = self.app.register("carol", "secret123")[0]["id"]
        app = self.app
        wid = app.create_workout(self.alice, workout(visibility="public"))[0]["id"]
        pid = app.create_post(self.alice, {"body": "hello", "visibility": "public"})["id"]
        self.kinds = {
            "workout": dict(id=wid, like=app.toggle_like, add=app.add_comment, delete=app.delete_comment,
                            get=app.get_workout, update=lambda user, data: app.update_workout(wid, user, data)),
            "post": dict(id=pid, like=app.toggle_post_like, add=app.add_post_comment, delete=app.delete_post_comment,
                         get=app.get_post, update=lambda user, data: app.update_post(pid, user, data)),
        }

    def each(self):
        for name, k in self.kinds.items():
            with self.subTest(kind=name):
                yield k

    def test_like_toggles_and_counts(self):
        for k in self.each():
            self.assertEqual(k["like"](k["id"], self.bob), {"liked": True, "likes": 1})
            self.assertEqual(k["like"](k["id"], self.alice), {"liked": True, "likes": 2})
            self.assertEqual(k["like"](k["id"], self.bob), {"liked": False, "likes": 1})

    def test_comments_add_delete_and_permissions(self):
        for k in self.each():
            comments = k["add"](k["id"], self.bob, "  nice  ")
            self.assertEqual([c["body"] for c in comments], ["nice"])
            self.assertTrue(comments[0]["can_delete"])
            cid = comments[0]["id"]
            self.assertTrue(k["get"](k["id"], self.alice)["comments"][0]["can_delete"])  # the owner may delete
            self.assertFalse(k["get"](k["id"], self.carol)["comments"][0]["can_delete"])
            with self.assertRaises(Forbidden):
                k["delete"](cid, self.carol)
            self.assertEqual(k["delete"](cid, self.alice), [])
            with self.assertRaises(NotFound):
                k["delete"](cid, self.alice)

    def test_ownership_and_hidden_private_items(self):
        for k in self.each():
            with self.assertRaises(Forbidden):
                k["update"](self.bob, {"visibility": "private"})
            k["update"](self.alice, {"visibility": "private"})
            for action in (lambda: k["like"](k["id"], self.bob), lambda: k["add"](k["id"], self.bob, "x"),
                           lambda: k["update"](self.bob, {}), lambda: k["get"](k["id"], self.bob)):
                with self.assertRaises(NotFound):
                    action()

    def test_update_applies_only_given_fields(self):
        updated = self.app.update_workout(self.kinds["workout"]["id"], self.alice, {"title": "Нове"})
        self.assertEqual((updated["title"], updated["visibility"]), ("Нове", "public"))
        updated = self.app.update_post(self.kinds["post"]["id"], self.alice, {})
        self.assertEqual((updated["body"], updated["visibility"]), ("hello", "public"))

    def test_profile_counts(self):
        self.app.follow(self.bob, "alice")
        self.app.create_post(self.alice, {"body": "secret", "visibility": "private"})
        self.app.create_workout(self.alice, workout(visibility="private"))
        as_bob = self.app.get_profile("alice", self.bob)
        self.assertEqual((as_bob["followers"], as_bob["following"], as_bob["workouts"], as_bob["posts"]), (1, 0, 1, 1))
        as_alice = self.app.get_profile("alice", self.alice)
        self.assertEqual((as_alice["workouts"], as_alice["posts"]), (2, 2))

    def test_get_my_profile_matches_get_profile(self):
        """Replaces the raw SQL that used to live in the GET /api/me route handler."""
        self.assertEqual(self.app.get_my_profile(self.alice), self.app.get_profile("alice", self.alice))
        self.assertTrue(self.app.get_my_profile(self.alice)["is_me"])


class LifecycleTests(unittest.TestCase):
    def test_close_is_idempotent(self):
        app, _ = make_app()
        app.close()
        app.close()
        with self.assertRaises(Exception):
            app._one("SELECT 1")

    def test_foreign_keys_stay_enabled(self):
        conn = connect()
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
