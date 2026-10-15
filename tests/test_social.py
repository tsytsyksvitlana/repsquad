import unittest

from backend.errors import Forbidden, NotFound, ValidationError
from tests.helpers import make_app, workout


class SocialTests(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.a, _t = self.app.register("alice", "secret123", "Аліса")
        self.b, _t = self.app.register("bob", "secret123", "Боб")
        self.c, _t = self.app.register("carol", "secret123", "Керол")

    def test_follow_unfollow_and_counters(self):
        p = self.app.follow(self.a["id"], "bob")
        self.assertTrue(p["followed_by_me"])
        self.assertEqual(p["followers"], 1)
        self.assertEqual(self.app.get_profile("alice", self.a["id"])["following"], 1)
        self.app.follow(self.a["id"], "bob")   # following again does not create a duplicate
        self.assertEqual(self.app.get_profile("bob", self.a["id"])["followers"], 1)
        p = self.app.unfollow(self.a["id"], "bob")
        self.assertEqual((p["followed_by_me"], p["followers"]), (False, 0))

    def test_cannot_follow_self_or_unknown(self):
        with self.assertRaises(ValidationError):
            self.app.follow(self.a["id"], "alice")
        with self.assertRaises(NotFound):
            self.app.follow(self.a["id"], "nobody")

    def test_feed_contains_only_followed_public_workouts(self):
        self.app.create_workout(self.b["id"], workout("bob-pub", "public"))
        self.app.create_workout(self.b["id"], workout("bob-priv", "private"))
        self.app.create_workout(self.c["id"], workout("carol-pub", "public"))
        self.app.create_workout(self.a["id"], workout("alice-own", "public"))
        self.assertEqual(self.app.feed(self.a["id"])["items"], [])
        self.app.create_post(self.b["id"], {"body": "bob-post"})
        self.app.create_post(self.a["id"], {"body": "alice-post"})
        # own posts appear in the feed (own workouts do not), other people's posts only after following
        self.assertEqual([i["body"] for i in self.app.feed(self.a["id"], kind="all")["items"]], ["alice-post"])
        self.app.follow(self.a["id"], "bob")
        self.assertEqual([w["title"] for w in self.app.feed(self.a["id"])["items"]], ["bob-pub"])
        self.assertEqual({i.get("title") or i["body"] for i in self.app.feed(self.a["id"], kind="all")["items"]},
                         {"bob-pub", "bob-post", "alice-post"})
        self.app.unfollow(self.a["id"], "bob")
        self.assertEqual(self.app.feed(self.a["id"])["items"], [])

    def test_discover_shows_all_public(self):
        self.app.create_workout(self.b["id"], workout("bob-pub", "public"))
        self.app.create_workout(self.c["id"], workout("carol-priv", "private"))
        self.assertEqual([w["title"] for w in self.app.discover(self.a["id"])["items"]], ["bob-pub"])

    def test_search_users(self):
        names = lambda q: [u["username"] for u in self.app.search_users(q, self.a["id"])]
        self.assertEqual(names("bo"), ["bob"])
        self.assertEqual(names("Керол"), ["carol"])
        self.assertEqual(sorted(names("")), ["alice", "bob", "carol"])
        self.assertEqual(names("%"), [])      # pattern characters are escaped
        self.assertEqual(names("_"), [])

    def test_like_toggle(self):
        w, _ = self.app.create_workout(self.b["id"], workout("t", "public"))
        self.assertEqual(self.app.toggle_like(w["id"], self.a["id"]), {"liked": True, "likes": 1})
        self.app.toggle_like(w["id"], self.c["id"])
        self.assertEqual(self.app.get_workout(w["id"], self.a["id"])["likes"], 2)
        self.assertTrue(self.app.get_workout(w["id"], self.a["id"])["liked_by_me"])
        self.assertEqual(self.app.toggle_like(w["id"], self.a["id"]), {"liked": False, "likes": 1})
        self.assertFalse(self.app.get_workout(w["id"], self.a["id"])["liked_by_me"])

    def test_comments_flow_and_permissions(self):
        w, _ = self.app.create_workout(self.b["id"], workout("t", "public"))
        self.app.add_comment(w["id"], self.a["id"], "  Круто!  ")
        comments = self.app.add_comment(w["id"], self.c["id"], "Згоден")
        self.assertEqual([c["body"] for c in comments], ["Круто!", "Згоден"])
        self.assertEqual(self.app.get_workout(w["id"], self.a["id"])["comments_count"], 2)
        by_alice = comments[0]["id"]
        # the comment author or the workout author may delete it, an outsider may not
        with self.assertRaises(Forbidden):
            self.app.delete_comment(by_alice, self.c["id"])
        self.app.delete_comment(by_alice, self.b["id"])          # workout author
        self.assertEqual(len(self.app.get_workout(w["id"], self.b["id"])["comments"]), 1)
        carol_comment = self.app.get_workout(w["id"], self.b["id"])["comments"][0]
        self.assertFalse([c for c in self.app.get_workout(w["id"], self.a["id"])["comments"] if c["can_delete"]])
        self.assertTrue(carol_comment["can_delete"])
        self.app.delete_comment(carol_comment["id"], self.c["id"])   # comment author
        self.assertEqual(self.app.get_workout(w["id"], self.b["id"])["comments"], [])

    def test_comment_validation(self):
        w, _ = self.app.create_workout(self.b["id"], workout("t", "public"))
        for bad in ("", "   ", None, "x" * 501):
            with self.assertRaises(ValidationError):
                self.app.add_comment(w["id"], self.a["id"], bad)
        with self.assertRaises(NotFound):
            self.app.delete_comment(9999, self.a["id"])

    def test_deleting_workout_removes_reactions(self):
        w, _ = self.app.create_workout(self.b["id"], workout("t", "public"))
        self.app.toggle_like(w["id"], self.a["id"])
        self.app.add_comment(w["id"], self.a["id"], "hi")
        self.app.delete_workout(w["id"], self.b["id"])
        self.assertEqual(self.app._one("SELECT COUNT(*) AS n FROM likes")["n"], 0)
        self.assertEqual(self.app._one("SELECT COUNT(*) AS n FROM comments")["n"], 0)


if __name__ == "__main__":
    unittest.main()
