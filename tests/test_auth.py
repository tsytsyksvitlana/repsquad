import unittest
from datetime import timedelta

from backend.errors import Conflict, Unauthorized, ValidationError
from backend.services import SESSION_TTL
from tests.helpers import DEFAULT_PASSWORD, ServiceTestCase, query_all, query_one


class AuthTests(ServiceTestCase):
    def test_register_returns_profile_and_token(self):
        user, token = self.register_user("Sportsman_1", display_name="Іван")
        self.assertEqual((user["username"], user["display_name"], user["is_me"]), ("Sportsman_1", "Іван", True))
        self.assertEqual(self.app.authenticate(token), user["id"])

    def test_display_name_defaults_to_username(self):
        user, _ = self.register_user("alice")
        self.assertEqual(user["display_name"], "alice")

    def test_username_rules(self):
        for bad in ("ab", "a" * 21, "with space", "укр", "a-b", "", None):
            with self.subTest(username=bad), self.assertRaises(ValidationError):
                self.register_user(bad)

    def test_password_rules(self):
        for bad in ("short", "", None, "x" * 129):
            with self.subTest(password=repr(bad)), self.assertRaises(ValidationError):
                self.register_user("alice", password=bad)

    def test_username_unique_case_insensitive(self):
        self.register_user("Alice")
        with self.assertRaises(Conflict):
            self.register_user("alice")

    def test_password_is_not_stored_in_plain_text(self):
        self.register_user("alice")
        row = query_one(self.app, "SELECT * FROM users WHERE username = 'alice'")
        self.assertNotIn(DEFAULT_PASSWORD, str(tuple(row)))
        self.assertEqual(len(row["password_hash"]), 64)

    def test_same_password_gives_different_hashes(self):
        self.register_user("alice")
        self.register_user("bob")
        hashes = {r["password_hash"] for r in query_all(self.app, "SELECT password_hash FROM users")}
        self.assertEqual(len(hashes), 2)

    def test_tokens_are_stored_hashed(self):
        _, token = self.register_user("alice")
        stored = query_one(self.app, "SELECT token_hash FROM sessions")["token_hash"]
        self.assertNotEqual(stored, token)

    def test_login_success_is_case_insensitive(self):
        self.register_user("alice")
        user, token = self.app.login("ALICE", DEFAULT_PASSWORD)
        self.assertEqual(user["username"], "alice")
        self.assertTrue(token)

    def test_login_failures_raise_unauthorized(self):
        self.register_user("alice")
        for username, password in (("alice", "wrong"), ("nobody", DEFAULT_PASSWORD), (None, None), ("alice", None)):
            with self.subTest(username=username, password=password), self.assertRaises(Unauthorized):
                self.app.login(username, password)

    def test_login_error_does_not_reveal_which_field_is_wrong(self):
        self.register_user("alice")
        msgs = set()
        for username, password in (("alice", "wrong"), ("nobody", DEFAULT_PASSWORD)):
            try:
                self.app.login(username, password)
            except Unauthorized as e:
                msgs.add(e.message)
        self.assertEqual(len(msgs), 1)

    def test_logout_invalidates_token(self):
        _, token = self.register_user("alice")
        self.app.logout(token)
        with self.assertRaises(Unauthorized):
            self.app.authenticate(token)

    def test_missing_or_bogus_token(self):
        for token in (None, "", "bogus"):
            with self.subTest(token=token), self.assertRaises(Unauthorized):
                self.app.authenticate(token)

    def test_session_expires(self):
        _, token = self.register_user("alice")
        self.clock.now += SESSION_TTL - timedelta(minutes=1)
        self.app.authenticate(token)
        self.clock.now += timedelta(minutes=2)
        with self.assertRaises(Unauthorized):
            self.app.authenticate(token)

    def test_profile_update(self):
        user, _ = self.register_user("alice")
        p = self.app.update_profile(user["id"], {"sport": "Кросфіт", "level": "Середній", "bio": "Привіт"})
        self.assertEqual((p["sport"], p["level"], p["bio"]), ("Кросфіт", "середній", "Привіт"))

    def test_profile_validation_errors(self):
        user, _ = self.register_user("alice")
        for patch in ({"level": "бог"}, {"display_name": "  "}, {"bio": "x" * 301}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                self.app.update_profile(user["id"], patch)


if __name__ == "__main__":
    unittest.main()
