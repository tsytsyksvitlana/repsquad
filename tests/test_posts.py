import unittest
from datetime import datetime, timedelta

from tests.helpers import PostTestCase, make_data_url, workout


class PostTests(PostTestCase):
    def test_create_defaults(self):
        p = self.create_post("Моя перша тренувальна неділя")
        self.assertEqual((p["type"], p["visibility"], p["is_mine"], p["image_url"]), ("post", "public", True, None))

    def test_create_validation_and_auth(self):
        invalid_payloads = (
            {}, {"body": "   "}, {"body": "x" * 1001},
            {"body": "hi", "visibility": "friends"},
            {"body": "hi", "image": make_data_url(b"not an image")},
            {"body": ""},
        )
        for bad in invalid_payloads:
            with self.subTest(payload=bad):
                self.assertEqual(self.call("POST", "/api/posts", bad)[0], 400)
        self.assertEqual(self.call("POST", "/api/posts", {"body": "x"}, token=None)[0], 401)

    def test_image_only_post_is_allowed_and_can_keep_empty_body_on_edit(self):
        p = self.create_post("", image=make_data_url())
        self.assertTrue(p["image_url"].endswith(f"/{p['id']}/image"))
        updated = self.call("PATCH", f"/api/posts/{p['id']}", {"body": "", "visibility": "private"})[1]
        self.assertEqual((updated["body"], updated["visibility"]), ("", "private"))

    def test_private_post_hidden_everywhere_from_others(self):
        self.call("POST", "/api/users/alice/follow", {}, token=self.bob)
        private = self.create_post("secret", visibility="private", image=make_data_url())
        public = self.create_post("open")

        for path in ("/api/feed", "/api/discover", "/api/users/alice/timeline"):
            with self.subTest(path=path):
                ids = [i["id"] for i in self.call("GET", path, token=self.bob)[1]["items"] if i["type"] == "post"]
                self.assertEqual(ids, [public["id"]])

        # Author still sees their own private post on their profile timeline.
        own = [i["id"] for i in self.call("GET", "/api/users/alice/timeline")[1]["items"]]
        self.assertEqual(sorted(own), sorted([private["id"], public["id"]]))

        # Profile counters count only what the viewer may see.
        self.assertEqual(self.call("GET", "/api/users/alice", token=self.bob)[1]["posts"], 1)
        self.assertEqual(self.call("GET", "/api/users/alice")[1]["posts"], 2)

        # Strangers cannot edit/delete, and cannot detect a private post.
        self.assertEqual(self.call("DELETE", f"/api/posts/{private['id']}", token=self.bob)[0], 404)
        self.assertEqual(self.call("DELETE", f"/api/posts/{public['id']}", token=self.bob)[0], 403)
        self.assertEqual(self.call("PATCH", f"/api/posts/{public['id']}", {"visibility": "private"}, token=self.bob)[0], 403)

    def test_kind_filter_and_mixed_ordering(self):
        self.call("POST", "/api/workouts", workout("Old", "public", date="2026-06-10"))
        self.clock.now = datetime(2026, 6, 15, 12, 0)
        p1 = self.create_post("first")
        self.call("POST", "/api/workouts", workout("Today", "public", date="2026-06-15"))
        self.clock.now += timedelta(hours=1)
        p2 = self.create_post("second")

        def kinds(kind, **q):
            r = self.call("GET", "/api/discover", query={"kind": kind, **q})[1]
            return [(i["type"], i.get("title") or i["body"]) for i in r["items"]], r["has_more"]

        everything, _ = kinds("all")
        self.assertEqual(everything, [("post", "second"), ("workout", "Today"), ("post", "first"), ("workout", "Old")])
        self.assertEqual(kinds("posts")[0], [("post", "second"), ("post", "first")])
        self.assertEqual(kinds("workouts")[0], [("workout", "Today"), ("workout", "Old")])
        self.assertEqual(self.call("GET", "/api/discover", query={"kind": "nope"})[0], 400)

        # Pagination walks across both kinds without gaps or duplicates.
        seen, offset = [], 0
        while True:
            page = self.call("GET", "/api/discover", query={"kind": "all", "limit": 3, "offset": offset})[1]
            seen += [(i["type"], i["id"]) for i in page["items"]]
            offset += 3
            if not page["has_more"]:
                break
        self.assertEqual(len(seen), 4)
        self.assertEqual(len(set(seen)), 4)
        self.assertEqual([item_id for kind, item_id in seen if kind == "post"], [p2["id"], p1["id"]])

    def test_update_and_delete(self):
        p = self.create_post("draft")
        out = self.call("PATCH", f"/api/posts/{p['id']}", {"body": "edited", "visibility": "private"})[1]
        self.assertEqual((out["body"], out["visibility"]), ("edited", "private"))
        self.assertEqual(self.call("PATCH", f"/api/posts/{p['id']}", {"body": "  "})[0], 400)
        self.assertEqual(self.call("DELETE", f"/api/posts/{p['id']}")[0], 200)
        self.assertEqual(self.call("DELETE", f"/api/posts/{p['id']}")[0], 404)

    def test_existing_workout_endpoints_unchanged(self):
        self.create_post("noise")
        self.call("POST", "/api/workouts", workout("W", "public"))
        items = self.call("GET", "/api/users/alice/workouts")[1]["items"]
        self.assertEqual([(i["type"], i["title"]) for i in items], [("workout", "W")])


if __name__ == "__main__":
    unittest.main()
