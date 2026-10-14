import base64
import unittest

from tests.helpers import Api, make_app, workout

# Smallest valid-looking headers: only the magic bytes matter for validation.
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20


def data_url(raw, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


class AvatarTests(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.api = Api(self.app)
        self.tok = self.signup("alice")

    def signup(self, name):
        return self.api.handle("POST", "/api/auth/register", None, {"username": name, "password": "secret123"})[1]["token"]

    def call(self, method, path, body=None, token=None):
        return self.api.handle(method, path, None, body, token or self.tok)

    def fetch(self, path):
        status, headers, body = self.api.raw("GET", path)  # public: <img> cannot send a token
        return status, headers, body

    def test_no_avatar_by_default(self):
        self.assertIsNone(self.call("GET", "/api/me")[1]["avatar_url"])
        self.assertEqual(self.fetch("/api/users/alice/avatar")[0], 404)

    def test_upload_serve_replace_delete(self):
        st, me = self.call("PUT", "/api/me/avatar", {"image": data_url(JPEG)})
        self.assertEqual(st, 200)
        url = me["avatar_url"]
        self.assertTrue(url.endswith("?v=1"), url)
        status, headers, body = self.fetch(url)  # public: <img> cannot send a token
        self.assertEqual((status, headers["content-type"], body), (200, "image/jpeg", JPEG))
        self.assertIn("immutable", headers["cache-control"])
        # replacing bumps the version so caches are busted
        me = self.call("PUT", "/api/me/avatar", {"image": data_url(PNG, "image/png")})[1]
        self.assertTrue(me["avatar_url"].endswith("?v=2"))
        self.assertEqual(self.fetch(me["avatar_url"])[1]["content-type"], "image/png")
        self.assertIsNone(self.call("DELETE", "/api/me/avatar")[1]["avatar_url"])
        self.assertEqual(self.fetch("/api/users/alice/avatar")[0], 404)

    def test_validation(self):
        for bad in (None, "", "%%%", data_url(b"not an image"), data_url(b"<svg onload=alert(1)>"),
                    data_url(JPEG + b"\x00" * 200_000)):
            self.assertEqual(self.call("PUT", "/api/me/avatar", {"image": bad})[0], 400, str(bad)[:30])
        self.assertEqual(self.api.handle("PUT", "/api/me/avatar", None, {"image": data_url(JPEG)}, None)[0], 401)

    def test_avatar_appears_in_author_and_comment_views(self):
        self.call("PUT", "/api/me/avatar", {"image": data_url(JPEG)})
        wid = self.call("POST", "/api/workouts", workout(visibility="public"))[1]["workout"]["id"]
        w = self.call("GET", f"/api/workouts/{wid}")[1]
        self.assertTrue(w["author"]["avatar_url"].startswith("/api/users/alice/avatar"))
        comments = self.call("POST", f"/api/workouts/{wid}/comments", {"body": "hi"})[1]["comments"]
        self.assertTrue(comments[0]["author"]["avatar_url"])
        bob = self.signup("bob")
        self.assertIsNone(self.call("POST", f"/api/workouts/{wid}/comments", {"body": "yo"}, token=bob)[1]["comments"][1]["author"]["avatar_url"])


if __name__ == "__main__":
    unittest.main()
