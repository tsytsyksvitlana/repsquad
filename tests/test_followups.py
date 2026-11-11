import base64
import logging
import unittest
from datetime import timedelta
from unittest import mock

from backend import server
from backend.errors import Unauthorized
from backend.services import SESSION_TTL
from tests.helpers import make_app, workout

JPEG = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 20).decode()


class SearchUsersTests(unittest.TestCase):
    def setUp(self):
        self.app, _ = make_app()
        self.ids = {n: self.app.register(n, "secret123")[0]["id"] for n in ("anna", "andy", "anton", "bob")}
        app = self.app
        app.set_avatar(self.ids["anna"], JPEG)
        app.set_avatar(self.ids["anna"], JPEG)  # version 2
        app.follow(self.ids["bob"], "anna")
        app.follow(self.ids["anton"], "anna")
        app.follow(self.ids["anna"], "andy")
        app.create_workout(self.ids["anna"], workout(visibility="public"))
        app.create_workout(self.ids["anna"], workout(visibility="private"))
        app.create_post(self.ids["anna"], {"body": "pub", "visibility": "public"})
        app.create_post(self.ids["anna"], {"body": "priv", "visibility": "private"})
        app.create_post(self.ids["andy"], {"body": "pub", "visibility": "public"})

    def test_search_equals_individual_profiles_for_every_viewer(self):
        for viewer in (*self.ids.values(), None):
            with self.subTest(viewer=viewer):
                found = self.app.search_users("an", viewer)
                self.assertEqual([u["username"] for u in found], ["andy", "anna", "anton"])
                self.assertEqual(found, [self.app.get_profile(u["username"], viewer) for u in found])

    def test_search_covers_user_without_avatar_and_self(self):
        found = {u["username"]: u for u in self.app.search_users("", self.ids["anna"])}
        self.assertIsNone(found["bob"]["avatar_url"])
        self.assertEqual(found["anna"]["avatar_url"], "/api/users/anna/avatar?v=2")
        self.assertTrue(found["anna"]["is_me"])
        self.assertTrue(found["andy"]["followed_by_me"])
        self.assertEqual((found["anna"]["workouts"], found["anna"]["posts"]), (2, 2))

    def test_empty_result(self):
        self.assertEqual(self.app.search_users("zzz", self.ids["bob"]), [])

    def test_number_of_queries_does_not_depend_on_result_size(self):
        def selects(q):
            seen = []
            self.app.conn.set_trace_callback(lambda sql: seen.append(sql) if sql.lstrip().startswith("SELECT") else None)
            try:
                self.app.search_users(q, self.ids["bob"])
            finally:
                self.app.conn.set_trace_callback(None)
            return len(seen)

        self.assertEqual(selects("anna"), selects(""))  # 1 user vs 4 users
        self.assertLessEqual(selects(""), 7)


class SessionCleanupTests(unittest.TestCase):
    def setUp(self):
        self.app, self.clock = make_app()
        self.app.register("alice", "secret123")

    def sessions(self):
        return self.app._one("SELECT COUNT(*) AS n FROM sessions")["n"]

    def test_expired_token_is_deleted_on_authenticate(self):
        token = self.app.login("alice", "secret123")[1]
        self.assertEqual(self.sessions(), 2)  # register + login
        self.clock.now += SESSION_TTL + timedelta(seconds=1)
        with self.assertRaises(Unauthorized) as cm:
            self.app.authenticate(token)
        self.assertEqual(cm.exception.message, "Сесія недійсна або завершилась")
        self.assertEqual(self.sessions(), 1)
        with self.assertRaises(Unauthorized):  # row is gone: same error as for an unknown token
            self.app.authenticate(token)

    def test_valid_token_is_kept(self):
        token = self.app.login("alice", "secret123")[1]
        self.clock.now += SESSION_TTL
        self.assertIsNotNone(self.app.authenticate(token))
        self.assertEqual(self.sessions(), 2)

    def test_new_session_purges_expired_ones_only(self):
        self.clock.now += SESSION_TTL - timedelta(days=1)
        fresh = self.app.login("alice", "secret123")[1]
        self.clock.now += timedelta(days=2)  # the register session is now expired, the login one is not
        self.app.register("bob", "secret123")
        self.assertEqual(self.sessions(), 2)  # login (alice) + register (bob)
        self.assertIsNotNone(self.app.authenticate(fresh))
        self.clock.now += SESSION_TTL + timedelta(days=1)
        self.app.login("alice", "secret123")
        self.assertEqual(self.sessions(), 1)


class ServeLoggingTests(unittest.TestCase):
    def test_serve_logs_the_url_through_the_repsquad_logger(self):
        with mock.patch.object(server.uvicorn, "run") as run, mock.patch.object(logging, "basicConfig"), \
                self.assertLogs("repsquad", logging.INFO) as logs:
            server.serve(port=8123, db_path=":memory:")
        run.assert_called_once()
        self.assertIn("http://localhost:8123", logs.output[0])

    def test_serve_logs_stop_message_on_ctrl_c(self):
        with mock.patch.object(server.uvicorn, "run", side_effect=KeyboardInterrupt), \
                mock.patch.object(logging, "basicConfig"), self.assertLogs("repsquad", logging.INFO) as logs:
            server.serve(db_path=":memory:")
        self.assertIn("Зупинено.", logs.output[-1])

    def test_console_logging_is_configured_only_without_handlers(self):
        with mock.patch.object(server.uvicorn, "run"), mock.patch.object(logging, "basicConfig") as basic:
            with mock.patch.object(logging.getLogger(), "handlers", []):
                server.serve(db_path=":memory:")
            basic.assert_called_once()
            basic.reset_mock()
            with mock.patch.object(logging.getLogger(), "handlers", [logging.NullHandler()]):
                server.serve(db_path=":memory:")
            basic.assert_not_called()


if __name__ == "__main__":
    unittest.main()
