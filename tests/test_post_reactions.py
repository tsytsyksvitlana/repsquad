import unittest

from tests.helpers import PostTestCase, SAMPLE_JPEG, count_rows, make_data_url


class PostReactionTests(PostTestCase):
    """Likes and comments on posts follow the same rules as for workouts."""

    def test_like_toggle_and_counters(self):
        p = self.create_post("hello")
        self.assertEqual((p["likes"], p["liked_by_me"], p["comments_count"]), (0, False, 0))
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {}, token=self.bob)[1], {"liked": True, "likes": 1})
        self.call("POST", f"/api/posts/{p['id']}/like", {})
        view = self.call("GET", f"/api/posts/{p['id']}", token=self.bob)[1]
        self.assertEqual((view["likes"], view["liked_by_me"]), (2, True))
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {}, token=self.bob)[1], {"liked": False, "likes": 1})
        feed_item = self.call("GET", "/api/discover", query={"kind": "posts"}, token=self.bob)[1]["items"][0]
        self.assertEqual((feed_item["likes"], feed_item["liked_by_me"]), (1, False))

    def test_comment_flow_and_permissions(self):
        p = self.create_post("hello")
        st, r = self.call("POST", f"/api/posts/{p['id']}/comments", {"body": "  Круто!  "}, token=self.bob)
        self.assertEqual((st, r["comments"][0]["body"], r["comments"][0]["can_delete"]), (201, "Круто!", True))
        cid = r["comments"][0]["id"]
        self.assertTrue(self.call("GET", f"/api/posts/{p['id']}")[1]["comments"][0]["can_delete"])  # post author may delete
        self.assertEqual(self.call("GET", "/api/discover", query={"kind": "posts"})[1]["items"][0]["comments_count"], 1)
        carol = self.signup_token("carol")
        self.assertEqual(self.call("DELETE", f"/api/post-comments/{cid}", token=carol)[0], 403)
        self.assertEqual(self.call("DELETE", f"/api/post-comments/{cid}")[0], 200)  # post author
        self.assertEqual(self.call("DELETE", f"/api/post-comments/{cid}")[0], 404)

    def test_comment_validation(self):
        p = self.create_post("hello")
        for bad in ("", "   ", "x" * 501, None):
            with self.subTest(body=repr(bad)):
                self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/comments", {"body": bad})[0], 400)

    def test_private_post_cannot_be_liked_or_commented_by_others(self):
        p = self.create_post("secret", visibility="private")
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {}, token=self.bob)[0], 404)
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/comments", {"body": "hi"}, token=self.bob)[0], 404)
        self.assertEqual(self.call("GET", f"/api/posts/{p['id']}", token=self.bob)[0], 404)
        self.assertEqual(self.call("POST", f"/api/posts/{p['id']}/like", {})[0], 200)  # author still can

    def test_reactions_and_image_are_removed_with_the_post(self):
        p = self.create_post("hello", image=make_data_url())
        self.call("POST", f"/api/posts/{p['id']}/like", {}, token=self.bob)
        self.call("POST", f"/api/posts/{p['id']}/comments", {"body": "hi"}, token=self.bob)
        self.call("DELETE", f"/api/posts/{p['id']}")
        for table in ("post_likes", "post_comments", "post_images"):
            with self.subTest(table=table):
                self.assertEqual(count_rows(self.app, table), 0)

    def test_reactions_require_login(self):
        p = self.create_post("hello")
        endpoints = (
            ("POST", f"/api/posts/{p['id']}/like"),
            ("POST", f"/api/posts/{p['id']}/comments"),
            ("GET", f"/api/posts/{p['id']}"),
            ("DELETE", "/api/post-comments/1"),
        )
        for method, path in endpoints:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, {"body": "x"}, token=None)[0], 401)


class PostImageHttpTests(PostTestCase):
    def test_image_requires_login_and_respects_privacy(self):
        public = self.create_post("p", image=make_data_url(), visibility="public")
        private = self.create_post("p", image=make_data_url(), visibility="private")
        self.assertEqual(self.raw("GET", public["image_url"])[0], 401)
        status, headers, body = self.raw("GET", public["image_url"], token=self.bob)
        self.assertEqual((status, headers["content-type"], body), (200, "image/jpeg", SAMPLE_JPEG))
        self.assertTrue(headers["cache-control"].startswith("private"))
        self.assertEqual(self.raw("GET", private["image_url"], token=self.bob)[0], 404)
        self.assertEqual(self.raw("GET", private["image_url"], token=self.token)[0], 200)


if __name__ == "__main__":
    unittest.main()
