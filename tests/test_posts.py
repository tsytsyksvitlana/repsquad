import base64
import unittest
from datetime import datetime, timedelta

from tests.helpers import Api, make_app, workout

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20


def data_url(raw=JPEG):
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode()


class PostCase(unittest.TestCase):
    """Shared fixtures: two users and small helpers for calling the API."""

    def setUp(self):
        self.app, self.clock = make_app()
        self.api = Api(self.app)
        self.alice = self.signup("alice")
        self.bob = self.signup("bob")

    def signup(self, name):
        return self.api.handle("POST", "/api/auth/register", None, {"username": name, "password": "secret123"})[1]["token"]

    def call(self, method, path, body=None, token=None, query=None):
        return self.api.handle(method, path, query, body, token or self.alice)

    def post(self, body="hello", token=None, **extra):
        st, r = self.call("POST", "/api/posts", {"body": body, **extra}, token)
        self.assertEqual(st, 201, r)
        return r


class PostTests(PostCase):
    def test_create_validation_and_defaults(self):
        p = self.post("Моя перша тренувальна неділя")
        self.assertEqual((p["type"], p["visibility"], p["is_mine"], p["image_url"]), ("post", "public", True, None))
        for bad in ({}, {"body": "   "}, {"body": "x" * 1001}, {"body": "hi", "visibility": "friends"},
                    {"body": "hi", "image": data_url(b"not an image")}, {"body": ""}):
            self.assertEqual(self.call("POST", "/api/posts", bad)[0], 400, bad)
        self.assertEqual(self.api.handle("POST", "/api/posts", None, {"body": "x"}, None)[0], 401)

    def test_image_only_post_is_allowed(self):
        p = self.post("", image=data_url())
        self.assertTrue(p["image_url"].endswith(f"/{p['id']}/image"))

    def test_private_post_hidden_everywhere_from_others(self):
        self.call("POST", "/api/users/alice/follow", {}, self.bob)
        private = self.post("secret", visibility="private", image=data_url())
        public = self.post("open")
        for path in ("/api/feed", "/api/discover", "/api/users/alice/timeline"):
            ids = [i["id"] for i in self.call("GET", path, token=self.bob)[1]["items"] if i["type"] == "post"]
            self.assertEqual(ids, [public["id"]], path)
        # the author still sees their own private post on their profile timeline
        own = [i["id"] for i in self.call("GET", "/api/users/alice/timeline")[1]["items"]]
        self.assertEqual(sorted(own), sorted([private["id"], public["id"]]))
        # profile counters only count what the viewer may see
        self.assertEqual(self.call("GET", "/api/users/alice", token=self.bob)[1]["posts"], 1)
        self.assertEqual(self.call("GET", "/api/users/alice")[1]["posts"], 2)
        # a stranger cannot edit/delete, and cannot even tell the private post exists
        self.assertEqual(self.call("DELETE", f"/api/posts/{private['id']}", token=self.bob)[0], 404)
        self.assertEqual(self.call("DELETE", f"/api/posts/{public['id']}", token=self.bob)[0], 403)
        self.assertEqual(self.call("PATCH", f"/api/posts/{public['id']}", {"visibility": "private"}, self.bob)[0], 403)

    def test_kind_filter_and_mixed_ordering(self):
        self.call("POST", "/api/workouts", workout("Old", "public", date="2026-06-10"))
        self.clock.now = datetime(2026, 6, 15, 12, 0)
        p1 = self.post("first")
        self.call("POST", "/api/workouts", workout("Today", "public", date="2026-06-15"))
        self.clock.now += timedelta(hours=1)
        p2 = self.post("second")

        def kinds(kind, **q):
            r = self.call("GET", "/api/discover", query={"kind": kind, **q})[1]
            return [(i["type"], i.get("title") or i["body"]) for i in r["items"]], r["has_more"]
        everything, _ = kinds("all")
        self.assertEqual(everything, [("post", "second"), ("workout", "Today"), ("post", "first"), ("workout", "Old")])
        self.assertEqual(kinds("posts")[0], [("post", "second"), ("post", "first")])
        self.assertEqual(kinds("workouts")[0], [("workout", "Today"), ("workout", "Old")])
        self.assertEqual(self.call("GET", "/api/discover", query={"kind": "nope"})[0], 400)
        # pagination walks across both kinds without gaps or duplicates
        seen, offset = [], 0
        while True:
            page = self.call("GET", "/api/discover", query={"kind": "all", "limit": 3, "offset": offset})[1]
            seen += [(i["type"], i["id"]) for i in page["items"]]
            offset += 3
            if not page["has_more"]:
                break
        self.assertEqual(len(seen), 4)
        self.assertEqual(len(set(seen)), 4)
        self.assertEqual((p1["id"], p2["id"]), (1, 2))

    def test_update_and_delete(self):
        p = self.post("draft")
        out = self.call("PATCH", f"/api/posts/{p['id']}", {"body": "edited", "visibility": "private"})[1]
        self.assertEqual((out["body"], out["visibility"]), ("edited", "private"))
        self.assertEqual(self.call("PATCH", f"/api/posts/{p['id']}", {"body": "  "})[0], 400)
        self.assertEqual(self.call("DELETE", f"/api/posts/{p['id']}")[0], 200)
        self.assertEqual(self.call("DELETE", f"/api/posts/{p['id']}")[0], 404)

    def test_existing_workout_endpoints_unchanged(self):
        self.post("noise")
        self.call("POST", "/api/workouts", workout("W", "public"))
        items = self.call("GET", "/api/users/alice/workouts")[1]["items"]
        self.assertEqual([(i["type"], i["title"]) for i in items], [("workout", "W")])


class PostReactionTests(PostCase):
    """Likes and comments on posts follow the same rules as for workouts."""

    def test_like_toggle_and_counters(self):
        p = self.post("hello")
        self.assertEqual((p["likes"], p["liked_by_me"], p["comments_count"]), (0, False, 0))
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {}, self.bob)[1], {"liked": True, "likes": 1})
        self.call("POST", f"/api/posts/{p['id']}/like", {})
        view = self.call("GET", f"/api/posts/{p['id']}", token=self.bob)[1]
        self.assertEqual((view["likes"], view["liked_by_me"]), (2, True))
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {}, self.bob)[1], {"liked": False, "likes": 1})
        feed_item = self.call("GET", "/api/discover", query={"kind": "posts"}, token=self.bob)[1]["items"][0]
        self.assertEqual((feed_item["likes"], feed_item["liked_by_me"]), (1, False))

    def test_comment_flow_and_permissions(self):
        p = self.post("hello")
        st, r = self.call("POST", f"/api/posts/{p['id']}/comments", {"body": "  Круто!  "}, self.bob)
        self.assertEqual((st, r["comments"][0]["body"], r["comments"][0]["can_delete"]), (201, "Круто!", True))
        cid = r["comments"][0]["id"]
        self.assertEqual(self.call("GET", f"/api/posts/{p['id']}")[1]["comments"][0]["can_delete"], True)  # the post author may delete
        self.assertEqual(self.call("GET", "/api/discover", query={"kind": "posts"})[1]["items"][0]["comments_count"], 1)
        carol = self.signup("carol")
        self.assertEqual(self.call("DELETE", f"/api/post-comments/{cid}", token=carol)[0], 403)
        self.assertEqual(self.call("DELETE", f"/api/post-comments/{cid}")[0], 200)  # post author
        self.assertEqual(self.call("DELETE", f"/api/post-comments/{cid}")[0], 404)

    def test_comment_validation(self):
        p = self.post("hello")
        for bad in ("", "   ", "x" * 501, None):
            self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/comments", {"body": bad})[0], 400, bad)

    def test_private_post_cannot_be_liked_or_commented_by_others(self):
        p = self.post("secret", visibility="private")
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {}, self.bob)[0], 404)
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/comments", {"body": "hi"}, self.bob)[0], 404)
        self.assertEqual(self.call("GET", f"/api/posts/{p['id']}", token=self.bob)[0], 404)
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {})[0], 200)  # the author still can

    def test_reactions_are_removed_with_the_post(self):
        p = self.post("hello")
        self.call("POST", f"/api/posts/{p['id']}/like", {}, self.bob)
        self.call("POST", f"/api/posts/{p['id']}/comments", {"body": "hi"}, self.bob)
        self.call("DELETE", f"/api/posts/{p['id']}")
        for table in ("post_likes", "post_comments"):
            self.assertEqual(self.app._one(f"SELECT COUNT(*) AS n FROM {table}")["n"], 0)

    def test_reactions_require_login(self):
        p = self.post("hello")
        for method, path in (("POST", f"/api/posts/{p['id']}/like"), ("POST", f"/api/posts/{p['id']}/comments"),
                             ("GET", f"/api/posts/{p['id']}"), ("DELETE", "/api/post-comments/1")):
            self.assertEqual(self.api.handle(method, path, None, {"body": "x"}, None)[0], 401, path)


class PostImageHttpTests(unittest.TestCase):
    def setUp(self):
        app, _ = make_app()
        self.api = Api(app)
        self.alice = self.api.handle("POST", "/api/auth/register", None, {"username": "alice", "password": "secret123"})[1]["token"]
        self.bob = self.api.handle("POST", "/api/auth/register", None, {"username": "bob", "password": "secret123"})[1]["token"]

    def make_post(self, visibility):
        return self.api.handle("POST", "/api/posts", None, {"body": "p", "image": data_url(), "visibility": visibility}, self.alice)[1]

    def fetch(self, path, token=None):
        return self.api.raw("GET", path, token)

    def test_image_requires_login_and_respects_privacy(self):
        public, private = self.make_post("public"), self.make_post("private")
        self.assertEqual(self.fetch(public["image_url"])[0], 401)
        status, headers, body = self.fetch(public["image_url"], self.bob)
        self.assertEqual((status, headers["content-type"], body), (200, "image/jpeg", JPEG))
        self.assertTrue(headers["cache-control"].startswith("private"))
        self.assertEqual(self.fetch(private["image_url"], self.bob)[0], 404)
        self.assertEqual(self.fetch(private["image_url"], self.alice)[0], 200)


if __name__ == "__main__":
    unittest.main()
