import json
import unittest

from tests.helpers import ApiTestCase, DEFAULT_PASSWORD, lift


class ApiTests(ApiTestCase):
    def test_auth_required_everywhere_except_public_routes(self):
        protected = (
            ("GET", "/api/me"),
            ("GET", "/api/feed"),
            ("GET", "/api/discover"),
            ("POST", "/api/workouts"),
            ("GET", "/api/workouts/1"),
            ("GET", "/api/users/alice"),
            ("GET", "/api/me/records"),
            ("POST", "/api/posts"),
            ("GET", "/api/videos"),
        )
        for method, path in protected:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, {}, token=None)[0], 401)
        self.assertEqual(self.call("GET", "/api/health", token=None)[0], 200)
        self.assertEqual(self.call("GET", "/api/me", token="bogus")[0], 401)

    def test_register_and_duplicate_conflict(self):
        token, _ = self.signup("alice")
        self.assertEqual(self.call("GET", "/api/me", token=token)[1]["username"], "alice")
        self.assertEqual(self.call("POST", "/api/auth/register", {"username": "alice", "password": DEFAULT_PASSWORD})[0], 409)

    def test_login_success_and_wrong_password(self):
        self.signup("alice")
        st, r = self.call("POST", "/api/auth/login", {"username": "alice", "password": DEFAULT_PASSWORD})
        self.assertEqual(st, 200)
        self.assertTrue(r["token"])
        self.assertEqual(self.call("POST", "/api/auth/login", {"username": "alice", "password": "nope"})[0], 401)

    def test_logout_revokes_session(self):
        token, _ = self.signup("alice")
        self.assertEqual(self.call("POST", "/api/auth/logout", {}, token=token)[0], 200)
        self.assertEqual(self.call("GET", "/api/me", token=token)[0], 401)

    def test_response_never_contains_password_data(self):
        token, _ = self.signup("alice")
        blob = json.dumps(self.call("GET", "/api/me", token=token)[1]) + json.dumps(self.call("GET", "/api/users", token=token)[1])
        for word in ("password", "salt", "hash"):
            with self.subTest(word=word):
                self.assertNotIn(word, blob)

    def test_workout_privacy_hides_from_other_users(self):
        ta, _ = self.signup("alice")
        tb, _ = self.signup("bob")
        st, r = self.call("POST", "/api/workouts", {"title": "Груди", "visibility": "private", "exercises": [lift("Жим", (5, 80))]}, token=ta)
        self.assertEqual(st, 201)
        wid = r["workout"]["id"]
        for method, path, body in (
            ("GET", f"/api/workouts/{wid}", None),
            ("POST", f"/api/workouts/{wid}/like", {}),
            ("PATCH", f"/api/workouts/{wid}", {"visibility": "public"}),
        ):
            with self.subTest(method=method, path=path):
                self.assertEqual(self.call(method, path, body, token=tb)[0], 404)

    def test_workout_update_and_delete_permissions(self):
        ta, _ = self.signup("alice")
        tb, _ = self.signup("bob")
        wid = self.call("POST", "/api/workouts", {"title": "Груди", "visibility": "private", "exercises": [lift("Жим", (5, 80))]}, token=ta)[1]["workout"]["id"]
        self.assertEqual(self.call("PATCH", f"/api/workouts/{wid}", {"visibility": "public"}, token=ta)[0], 200)
        self.assertEqual(self.call("GET", f"/api/workouts/{wid}", token=tb)[0], 200)
        self.assertEqual(self.call("PATCH", f"/api/workouts/{wid}", {"title": "x"}, token=tb)[0], 403)
        self.assertEqual(self.call("DELETE", f"/api/workouts/{wid}", token=tb)[0], 403)
        self.assertEqual(self.call("DELETE", f"/api/workouts/{wid}", token=ta)[0], 200)
        self.assertEqual(self.call("GET", f"/api/workouts/{wid}", token=ta)[0], 404)

    def test_validation_errors_are_400(self):
        ta, _ = self.signup("alice")
        cases = (
            ("POST", "/api/workouts", {"title": "x"}, ta),
            ("POST", "/api/workouts", [], ta),
            ("POST", "/api/auth/login", "текст", None),
        )
        for method, path, body, token in cases:
            with self.subTest(path=path, body=body):
                self.assertEqual(self.call(method, path, body, token=token)[0], 400)

    def test_follow_feed_comment_flow(self):
        ta, _ = self.signup("alice")
        tb, _ = self.signup("bob")
        _, r = self.call("POST", "/api/workouts", {"title": "Pub", "visibility": "public", "exercises": [lift("Жим", (5, 80))]}, token=ta)
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
        ta, _ = self.signup("alice")
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


if __name__ == "__main__":
    unittest.main()
