import unittest
from datetime import timedelta

from backend.errors import Conflict, Unauthorized, ValidationError
from backend.services import SESSION_TTL
from tests.helpers import make_app


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.app, self.clock = make_app()

    def test_register_returns_profile_and_token(self):
        user, token = self.app.register("Sportsman_1", "secret123", "Іван")
        self.assertEqual((user["username"], user["display_name"], user["is_me"]), ("Sportsman_1", "Іван", True))
        self.assertEqual(self.app.authenticate(token), user["id"])

    def test_display_name_defaults_to_username(self):
        user, _ = self.app.register("alice", "secret123")
        self.assertEqual(user["display_name"], "alice")

    def test_username_rules(self):
        for bad in ("ab", "a" * 21, "with space", "укр", "a-b", "", None):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.app.register(bad, "secret123")

    def test_password_rules(self):
        for bad in ("short", "", None, "x" * 129):
            with self.assertRaises(ValidationError, msg=repr(bad)):
                self.app.register("alice", bad)

    def test_username_unique_case_insensitive(self):
        self.app.register("Alice", "secret123")
        with self.assertRaises(Conflict):
            self.app.register("alice", "secret123")

    def test_password_is_not_stored_in_plain_text(self):
        self.app.register("alice", "secret123")
        row = self.app._one("SELECT * FROM users WHERE username = 'alice'")
        self.assertNotIn("secret123", str(tuple(row)))
        self.assertEqual(len(row["password_hash"]), 64)

    def test_same_password_gives_different_hashes(self):
        self.app.register("alice", "secret123")
        self.app.register("bob", "secret123")
        hashes = {r["password_hash"] for r in self.app._all("SELECT password_hash FROM users")}
        self.assertEqual(len(hashes), 2)

    def test_tokens_are_stored_hashed(self):
        _, token = self.app.register("alice", "secret123")
        stored = self.app._one("SELECT token_hash FROM sessions")["token_hash"]
        self.assertNotEqual(stored, token)

    def test_login_success_and_failures(self):
        self.app.register("alice", "secret123")
        user, token = self.app.login("ALICE", "secret123")
        self.assertEqual(user["username"], "alice")
        self.assertTrue(token)
        for u, p in (("alice", "wrong"), ("nobody", "secret123"), (None, None), ("alice", None)):
            with self.assertRaises(Unauthorized):
                self.app.login(u, p)

    def test_login_error_does_not_reveal_which_field_is_wrong(self):
        self.app.register("alice", "secret123")
        msgs = set()
        for u, p in (("alice", "wrong"), ("nobody", "secret123")):
            try:
                self.app.login(u, p)
            except Unauthorized as e:
                msgs.add(e.message)
        self.assertEqual(len(msgs), 1)

    def test_logout_invalidates_token(self):
        _, token = self.app.register("alice", "secret123")
        self.app.logout(token)
        with self.assertRaises(Unauthorized):
            self.app.authenticate(token)

    def test_missing_or_bogus_token(self):
        for t in (None, "", "bogus"):
            with self.assertRaises(Unauthorized):
                self.app.authenticate(t)

    def test_session_expires(self):
        _, token = self.app.register("alice", "secret123")
        self.clock.now += SESSION_TTL - timedelta(minutes=1)
        self.app.authenticate(token)
        self.clock.now += timedelta(minutes=2)
        with self.assertRaises(Unauthorized):
            self.app.authenticate(token)

    def test_profile_update_and_validation(self):
        user, _ = self.app.register("alice", "secret123")
        p = self.app.update_profile(user["id"], {"sport": "Кросфіт", "level": "Середній", "bio": "Привіт"})
        self.assertEqual((p["sport"], p["level"], p["bio"]), ("Кросфіт", "середній", "Привіт"))
        with self.assertRaises(ValidationError):
            self.app.update_profile(user["id"], {"level": "бог"})
        with self.assertRaises(ValidationError):
            self.app.update_profile(user["id"], {"display_name": "  "})
        with self.assertRaises(ValidationError):
            self.app.update_profile(user["id"], {"bio": "x" * 301})


if __name__ == "__main__":
    unittest.main()
