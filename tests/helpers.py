"""Shared fixtures, assertions, and base TestCases for the RepSquad test suite."""
import base64
import os
import weakref
from contextlib import contextmanager
from datetime import datetime
import unittest
from unittest import mock

from backend.services import RepSquad

DEFAULT_PASSWORD = "secret123"

# Smallest valid-looking headers: only the magic bytes matter for image validation.
SAMPLE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
SAMPLE_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
SAMPLE_WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 16

_KNOWN_TABLES = frozenset({
    "users", "sessions", "posts", "post_images", "post_likes",
    "post_comments", "workouts", "sets", "likes", "comments",
})
_UNSET = object()


def make_data_url(raw=SAMPLE_JPEG, mime="image/jpeg"):
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


class Clock:
    def __init__(self, start=datetime(2026, 6, 15, 12, 0)):
        self.now = start

    def __call__(self):
        return self.now


def make_app():
    clock = Clock()
    app = RepSquad(":memory:", clock=clock, pbkdf2_iterations=1000)
    weakref.finalize(app, app.conn.close)  # closes the connection when the app is collected or at exit
    return app, clock


def workout(title="Ноги", visibility="private", exercises=None, date="2026-06-15"):
    payload = {
        "title": title,
        "date": date,
        "exercises": [{"name": "Присідання зі штангою", "sets": [{"reps": 5, "weight_kg": 100}]}]
        if exercises is None else exercises,
    }
    if visibility is not None:
        payload["visibility"] = visibility
    return payload


def lift(name, *sets):
    return {"name": name, "sets": [{"reps": r, "weight_kg": w} for r, w in sets]}


def query_one(app, sql, params=()):
    return app.conn.execute(sql, params).fetchone()


def query_all(app, sql, params=()):
    return app.conn.execute(sql, params).fetchall()


def execute_sql(app, sql, params=()):
    with app.conn:
        app.conn.execute(sql, params)


def count_rows(app, table):
    if table not in _KNOWN_TABLES:
        raise ValueError(f"Unknown test table: {table}")
    return query_one(app, f"SELECT COUNT(*) AS n FROM {table}")["n"]


@contextmanager
def trace_select_queries(app):
    """Counts SQL SELECT statements executed against `app` inside the with-block."""
    seen = []
    app.conn.set_trace_callback(lambda sql: seen.append(sql) if sql.lstrip().startswith("SELECT") else None)
    try:
        yield seen
    finally:
        app.conn.set_trace_callback(None)


def patch_env(test_case, clear_keys=(), **values):
    """Applies an isolated os.environ patch that is automatically restored on cleanup."""
    patcher = mock.patch.dict(os.environ, values)
    patcher.start()
    test_case.addCleanup(patcher.stop)
    for key in clear_keys:
        os.environ.pop(key, None)


class Api:
    """Test adapter: `handle(method, path, query, body, token) -> (status, json)` on top of FastAPI.

    Requests go through FastAPI's TestClient, i.e. the real ASGI application (routing, dependencies, validation,
    error handlers), without opening a network socket."""

    def __init__(self, service, ai_chat=None, static_dir=None):
        from fastapi.testclient import TestClient
        from backend.api import FRONTEND_DIST, create_app
        self.app = service
        self.fastapi = create_app(service, ai_chat=ai_chat, static_dir=static_dir or FRONTEND_DIST)
        self.client = TestClient(self.fastapi)

    @property
    def ai_chat(self):
        return self.fastapi.state.ai_chat

    @ai_chat.setter
    def ai_chat(self, chat):
        self.fastapi.state.ai_chat = chat

    def handle(self, method, path, query=None, body=None, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = self.client.request(method, path, params=query, json=body, headers=headers)
        return r.status_code, r.json()

    def raw(self, method, path, token=None, **kwargs):
        """Raw response (status, headers, bytes) for binary files, static assets, and malformed payloads."""
        headers = dict(kwargs.pop("headers", {}) or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        r = self.client.request(method, path, headers=headers, **kwargs)
        return r.status_code, r.headers, r.content


class ServiceTestCase(unittest.TestCase):
    """Base TestCase providing an isolated in-memory RepSquad service and automatic cleanup."""

    def setUp(self):
        self.app, self.clock = make_app()
        self.addCleanup(self.app.close)

    def register_user(self, username="alice", password=DEFAULT_PASSWORD, display_name=None):
        return self.app.register(username, password, display_name)


class ApiTestCase(unittest.TestCase):
    """Base TestCase providing an isolated ASGI Api client, automatic DB cleanup, and auth helpers."""

    default_username = None

    def make_ai_chat(self):
        return None

    def setUp(self):
        self.app, self.clock = make_app()
        self.addCleanup(self.app.close)
        self.api = Api(self.app, ai_chat=self.make_ai_chat())
        self.token = self.signup_token(self.default_username) if self.default_username else None

    def signup(self, username="alice", password=DEFAULT_PASSWORD, display_name=None):
        body = {"username": username, "password": password}
        if display_name is not None:
            body["display_name"] = display_name
        st, r = self.api.handle("POST", "/api/auth/register", body=body)
        self.assertEqual(st, 201, r)
        return r["token"], r["user"]

    def signup_token(self, username="alice", password=DEFAULT_PASSWORD, display_name=None):
        return self.signup(username, password, display_name)[0]

    def call(self, method, path, body=None, query=None, token=_UNSET):
        """Calls the API; omits Authorization when `token=None`, otherwise defaults to `self.token`."""
        effective = self.token if token is _UNSET else token
        return self.api.handle(method, path, query, body, effective)

    def raw(self, method, path, token=None, **kwargs):
        return self.api.raw(method, path, token=token, **kwargs)


class PostTestCase(ApiTestCase):
    """Shared fixtures for post CRUD, reaction, and post-image HTTP tests."""

    default_username = "alice"

    def setUp(self):
        super().setUp()
        self.bob = self.signup_token("bob")

    def create_post(self, body="hello", token=_UNSET, **extra):
        st, r = self.call("POST", "/api/posts", {"body": body, **extra}, token=token)
        self.assertEqual(st, 201, r)
        return r
