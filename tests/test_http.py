import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import Api, DEFAULT_PASSWORD, lift, make_app


class HttpTests(unittest.TestCase):
    """The ASGI application itself: static files, error format, HTTP verbs, generated OpenAPI docs."""

    @classmethod
    def setUpClass(cls):
        app, _ = make_app()
        cls.addClassCleanup(app.close)
        # A tiny fake build output keeps the test independent of the real frontend build.
        cls.static = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.static.cleanup)
        (Path(cls.static.name) / "index.html").write_text("<title>RepSquad</title>", encoding="utf-8")
        cls.api = Api(app, static_dir=cls.static.name)

    def req(self, method, path, body=None, token=None):
        return self.api.handle(method, path, None, body, token)

    def test_index_and_static_security_headers(self):
        status, headers, body = self.api.raw("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"RepSquad", body)
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["cache-control"], "no-store")

    def test_missing_frontend_build_gives_a_hint(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        app, _ = make_app()
        self.addCleanup(app.close)
        status, _, body = Api(app, static_dir=empty.name).raw("GET", "/")
        self.assertEqual(status, 503)
        self.assertIn(b"npm run build", body)

    def test_path_traversal_blocked(self):
        for path in ("/..%2Frun.py", "/../run.py", "/%2e%2e/run.py", "/assets/../../run.py"):
            with self.subTest(path=path):
                self.assertEqual(self.api.raw("GET", path)[0], 404)

    def test_unknown_api_path_is_json_404_not_the_frontend(self):
        status, _, body = self.api.raw("GET", "/api/nope")
        self.assertEqual((status, json.loads(body)), (404, {"error": "Маршрут не знайдено"}))

    def test_full_flow_including_patch_and_delete_verbs(self):
        st, r = self.req("POST", "/api/auth/register", {"username": "http_user", "password": DEFAULT_PASSWORD})
        self.assertEqual(st, 201)
        tok = r["token"]
        st, r = self.req("POST", "/api/workouts", {"title": "t", "exercises": [lift("Жим", (5, 50))]}, tok)
        self.assertEqual(st, 201)
        wid = r["workout"]["id"]
        self.assertEqual(self.req("PATCH", f"/api/workouts/{wid}", {"visibility": "public"}, tok)[1]["visibility"], "public")
        self.assertEqual(self.req("DELETE", f"/api/workouts/{wid}", None, tok)[0], 200)
        self.assertEqual(self.req("GET", "/api/me")[0], 401)

    def test_invalid_json_returns_400_with_error_format(self):
        status, _, body = self.api.raw("POST", "/api/auth/login", content=b"{oops",
                                       headers={"Content-Type": "application/json"})
        self.assertEqual((status, json.loads(body)), (400, {"error": "Некоректний JSON"}))

    def test_non_object_json_shapes_return_400(self):
        for body in ([1, 2], "text", 5):
            with self.subTest(body=body):
                st, payload = self.req("POST", "/api/auth/login", body)
                self.assertEqual((st, payload), (400, {"error": "Очікується JSON-об'єкт"}))

    def test_invalid_field_type_returns_400_with_field_name(self):
        st, payload = self.req("POST", "/api/auth/login", {"username": 123})
        self.assertEqual(st, 400)
        self.assertIn("username", payload["error"])

    def test_openapi_documentation_is_generated(self):
        status, _, body = self.api.raw("GET", "/openapi.json")
        self.assertEqual(status, 200)
        schema = json.loads(body)
        self.assertIn("/api/posts/{pid}/like", schema["paths"])
        self.assertIn("post", schema["paths"]["/api/workouts"])
        self.assertEqual(self.api.raw("GET", "/docs")[0], 200)

    def test_non_numeric_ids_do_not_match_a_route(self):
        tok = self.req("POST", "/api/auth/register", {"username": "ids_user", "password": DEFAULT_PASSWORD})[1]["token"]
        self.assertEqual(self.req("GET", "/api/workouts/abc", None, tok)[0], 404)


if __name__ == "__main__":
    unittest.main()
