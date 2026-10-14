import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import Api, lift, make_app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.api = Api(self.app)

    def call(self, method, path, body=None, query=None, token=None):
        return self.api.handle(method, path, query, body, token)

    def signup(self, username="alice"):
        st, r = self.call("POST", "/api/auth/register", {"username": username, "password": "secret123"})
        self.assertEqual(st, 201, r)
        return r["token"], r["user"]

    def test_auth_required_everywhere_except_public_routes(self):
        for method, path in (("GET", "/api/me"), ("GET", "/api/feed"), ("GET", "/api/discover"), ("POST", "/api/workouts"),
                             ("GET", "/api/workouts/1"), ("GET", "/api/users/alice"), ("GET", "/api/me/records")):
            self.assertEqual(self.call(method, path, {})[0], 401, path)
        self.assertEqual(self.call("GET", "/api/health")[0], 200)
        self.assertEqual(self.call("GET", "/api/me", token="bogus")[0], 401)

    def test_register_login_me_logout(self):
        token, user = self.signup()
        self.assertEqual(self.call("GET", "/api/me", token=token)[1]["username"], "alice")
        st, r = self.call("POST", "/api/auth/login", {"username": "alice", "password": "secret123"})
        self.assertEqual(st, 200)
        self.assertEqual(self.call("POST", "/api/auth/login", {"username": "alice", "password": "nope"})[0], 401)
        self.assertEqual(self.call("POST", "/api/auth/register", {"username": "alice", "password": "secret123"})[0], 409)
        self.assertEqual(self.call("POST", "/api/auth/logout", {}, token=token)[0], 200)
        self.assertEqual(self.call("GET", "/api/me", token=token)[0], 401)

    def test_response_never_contains_password_data(self):
        token, _ = self.signup()
        blob = json.dumps(self.call("GET", "/api/me", token=token)[1]) + json.dumps(self.call("GET", "/api/users", token=token)[1])
        for word in ("password", "salt", "hash"):
            self.assertNotIn(word, blob)

    def test_workout_lifecycle_and_privacy_over_api(self):
        ta, _ = self.signup("alice")
        tb, _ = self.signup("bob")
        body = {"title": "Груди", "visibility": "private", "exercises": [lift("Жим", (5, 80))]}
        st, r = self.call("POST", "/api/workouts", body, token=ta)
        self.assertEqual(st, 201)
        wid = r["workout"]["id"]
        self.assertEqual(self.call("GET", f"/api/workouts/{wid}", token=tb)[0], 404)
        self.assertEqual(self.call("POST", f"/api/workouts/{wid}/like", {}, token=tb)[0], 404)
        self.assertEqual(self.call("PATCH", f"/api/workouts/{wid}", {"visibility": "public"}, token=tb)[0], 404)
        self.assertEqual(self.call("PATCH", f"/api/workouts/{wid}", {"visibility": "public"}, token=ta)[0], 200)
        self.assertEqual(self.call("GET", f"/api/workouts/{wid}", token=tb)[0], 200)
        self.assertEqual(self.call("PATCH", f"/api/workouts/{wid}", {"title": "x"}, token=tb)[0], 403)
        self.assertEqual(self.call("DELETE", f"/api/workouts/{wid}", token=tb)[0], 403)
        self.assertEqual(self.call("DELETE", f"/api/workouts/{wid}", token=ta)[0], 200)
        self.assertEqual(self.call("GET", f"/api/workouts/{wid}", token=ta)[0], 404)

    def test_validation_errors_are_400(self):
        ta, _ = self.signup()
        self.assertEqual(self.call("POST", "/api/workouts", {"title": "x"}, token=ta)[0], 400)
        self.assertEqual(self.call("POST", "/api/workouts", [], token=ta)[0], 400)
        self.assertEqual(self.call("POST", "/api/auth/login", "текст")[0], 400)

    def test_follow_feed_comment_flow(self):
        ta, _ = self.signup("alice")
        tb, _ = self.signup("bob")
        _, r = self.call("POST", "/api/workouts", {"title": "Pub", "visibility": "public",
                                                   "exercises": [lift("Жим", (5, 80))]}, token=ta)
        wid = r["workout"]["id"]
        self.assertEqual(self.call("GET", "/api/feed", token=tb)[1]["items"], [])
        self.assertEqual(self.call("POST", "/api/users/alice/follow", {}, token=tb)[0], 200)
        self.assertEqual(len(self.call("GET", "/api/feed", token=tb)[1]["items"]), 1)
        self.assertEqual(self.call("POST", f"/api/workouts/{wid}/like", {}, token=tb)[1], {"liked": True, "likes": 1})
        st, r = self.call("POST", f"/api/workouts/{wid}/comments", {"body": "Круто"}, token=tb)
        self.assertEqual((st, r["comments"][0]["body"]), (201, "Круто"))
        cid = r["comments"][0]["id"]
        self.assertEqual(self.call("DELETE", f"/api/comments/{cid}", token=tb)[0], 200)
        self.assertEqual(self.call("DELETE", "/api/users/alice/follow", token=tb)[0], 200)
        self.assertEqual(self.call("GET", "/api/feed", token=tb)[1]["items"], [])

    def test_records_progress_exercises_routes(self):
        ta, _ = self.signup()
        self.call("POST", "/api/workouts", {"title": "t", "date": "2026-06-01", "exercises": [lift("Жим", (5, 80))]}, token=ta)
        _, r = self.call("POST", "/api/workouts", {"title": "t", "date": "2026-06-08", "exercises": [lift("Жим", (5, 90))]}, token=ta)
        self.assertEqual(r["new_records"][0]["weight_kg"], 90.0)
        self.assertEqual(self.call("GET", "/api/me/records", token=ta)[1]["items"][0]["max_weight_kg"], 90.0)
        self.assertEqual(len(self.call("GET", "/api/me/progress", query={"exercise": "Жим"}, token=ta)[1]["points"]), 2)
        self.assertEqual(self.call("GET", "/api/me/progress", query={"exercise": "Х"}, token=ta)[0], 404)
        self.assertIn("Жим", self.call("GET", "/api/exercises", token=ta)[1]["items"])

    def test_unknown_route_and_wrong_method(self):
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)
        self.assertEqual(self.call("PUT", "/api/feed")[0], 405)


class HttpTests(unittest.TestCase):
    """The ASGI application itself: static files, error format, verbs, generated documentation."""

    @classmethod
    def setUpClass(cls):
        app, _ = make_app()
        # A tiny fake build output keeps the test independent of the real frontend build.
        cls.static = tempfile.TemporaryDirectory()
        (Path(cls.static.name) / "index.html").write_text("<title>RepSquad</title>", encoding="utf-8")
        cls.api = Api(app, static_dir=cls.static.name)

    @classmethod
    def tearDownClass(cls):
        cls.static.cleanup()

    def req(self, method, path, body=None, token=None):
        return self.api.handle(method, path, None, body, token)

    def test_index_and_static(self):
        status, headers, body = self.api.raw("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"RepSquad", body)
        self.assertEqual(headers["x-content-type-options"], "nosniff")
        self.assertEqual(headers["cache-control"], "no-store")

    def test_missing_frontend_build_gives_a_hint(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        status, _, body = Api(make_app()[0], static_dir=empty.name).raw("GET", "/")
        self.assertEqual(status, 503)
        self.assertIn(b"npm run build", body)

    def test_path_traversal_blocked(self):
        for path in ("/..%2Frun.py", "/../run.py", "/%2e%2e/run.py", "/assets/../../run.py"):
            self.assertEqual(self.api.raw("GET", path)[0], 404, path)

    def test_unknown_api_path_is_json_404_not_the_frontend(self):
        status, headers, body = self.api.raw("GET", "/api/nope")
        self.assertEqual((status, json.loads(body)), (404, {"error": "Маршрут не знайдено"}))

    def test_full_flow_including_patch_and_delete_verbs(self):
        st, r = self.req("POST", "/api/auth/register", {"username": "http_user", "password": "secret123"})
        self.assertEqual(st, 201)
        tok = r["token"]
        st, r = self.req("POST", "/api/workouts", {"title": "t", "exercises": [lift("Жим", (5, 50))]}, tok)
        wid = r["workout"]["id"]
        self.assertEqual(self.req("PATCH", f"/api/workouts/{wid}", {"visibility": "public"}, tok)[1]["visibility"], "public")
        self.assertEqual(self.req("DELETE", f"/api/workouts/{wid}", None, tok)[0], 200)
        self.assertEqual(self.req("GET", "/api/me")[0], 401)

    def test_bad_json_and_wrong_shapes_are_400_with_our_error_format(self):
        r = self.api.client.post("/api/auth/login", content=b"{oops", headers={"Content-Type": "application/json"})
        self.assertEqual((r.status_code, r.json()), (400, {"error": "Некоректний JSON"}))
        for body in ([1, 2], "text", 5):
            st, payload = self.req("POST", "/api/auth/login", body)
            self.assertEqual((st, payload), (400, {"error": "Очікується JSON-об'єкт"}), body)
        st, payload = self.req("POST", "/api/auth/login", {"username": 123})
        self.assertEqual(st, 400)
        self.assertIn("username", payload["error"])

    def test_openapi_documentation_is_generated(self):
        schema = self.api.client.get("/openapi.json").json()
        self.assertIn("/api/posts/{pid}/like", schema["paths"])
        self.assertIn("post", schema["paths"]["/api/workouts"])
        self.assertEqual(self.api.raw("GET", "/docs")[0], 200)

    def test_non_numeric_ids_do_not_match_a_route(self):
        tok = self.req("POST", "/api/auth/register", {"username": "ids_user", "password": "secret123"})[1]["token"]
        self.assertEqual(self.req("GET", "/api/workouts/abc", None, tok)[0], 404)


if __name__ == "__main__":
    unittest.main()
