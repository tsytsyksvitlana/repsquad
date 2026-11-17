import unittest

from tests.helpers import ApiTestCase, SAMPLE_JPEG, SAMPLE_PNG, SAMPLE_WEBP, make_data_url, workout


class AvatarTests(ApiTestCase):
    default_username = "alice"

    def test_no_avatar_by_default(self):
        self.assertIsNone(self.call("GET", "/api/me")[1]["avatar_url"])
        self.assertEqual(self.raw("GET", "/api/users/alice/avatar")[0], 404)

    def test_upload_serve_replace_and_delete(self):
        st, me = self.call("PUT", "/api/me/avatar", {"image": make_data_url(SAMPLE_JPEG)})
        self.assertEqual(st, 200)
        url = me["avatar_url"]
        self.assertTrue(url.endswith("?v=1"), url)

        status, headers, body = self.raw("GET", url)  # public: <img> cannot send a token
        self.assertEqual((status, headers["content-type"], body), (200, "image/jpeg", SAMPLE_JPEG))
        self.assertIn("immutable", headers["cache-control"])

        # Replacing bumps the version so browser caches are busted.
        me = self.call("PUT", "/api/me/avatar", {"image": make_data_url(SAMPLE_PNG, "image/png")})[1]
        self.assertTrue(me["avatar_url"].endswith("?v=2"))
        self.assertEqual(self.raw("GET", me["avatar_url"])[1]["content-type"], "image/png")

        me = self.call("PUT", "/api/me/avatar", {"image": make_data_url(SAMPLE_WEBP, "image/webp")})[1]
        self.assertTrue(me["avatar_url"].endswith("?v=3"))
        self.assertEqual(self.raw("GET", me["avatar_url"])[1]["content-type"], "image/webp")

        self.assertIsNone(self.call("DELETE", "/api/me/avatar")[1]["avatar_url"])
        self.assertEqual(self.raw("GET", "/api/users/alice/avatar")[0], 404)

    def test_validation_and_auth(self):
        invalid_images = (
            None, "", "%%%", make_data_url(b"not an image"),
            make_data_url(b"<svg onload=alert(1)>"),
            make_data_url(SAMPLE_JPEG + b"\x00" * 200_000),
        )
        for bad in invalid_images:
            with self.subTest(image=str(bad)[:30]):
                self.assertEqual(self.call("PUT", "/api/me/avatar", {"image": bad})[0], 400)
        self.assertEqual(self.call("PUT", "/api/me/avatar", {"image": make_data_url(SAMPLE_JPEG)}, token=None)[0], 401)

    def test_avatar_appears_in_author_and_comment_views(self):
        self.call("PUT", "/api/me/avatar", {"image": make_data_url(SAMPLE_JPEG)})
        wid = self.call("POST", "/api/workouts", workout(visibility="public"))[1]["workout"]["id"]
        w = self.call("GET", f"/api/workouts/{wid}")[1]
        self.assertTrue(w["author"]["avatar_url"].startswith("/api/users/alice/avatar"))
        comments = self.call("POST", f"/api/workouts/{wid}/comments", {"body": "hi"})[1]["comments"]
        self.assertTrue(comments[0]["author"]["avatar_url"])
        bob = self.signup_token("bob")
        bob_comments = self.call("POST", f"/api/workouts/{wid}/comments", {"body": "yo"}, token=bob)[1]["comments"]
        self.assertIsNone(bob_comments[1]["author"]["avatar_url"])


if __name__ == "__main__":
    unittest.main()
