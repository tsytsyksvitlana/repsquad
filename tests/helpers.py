from datetime import datetime

from backend.services import RepSquad


class Clock:
    def __init__(self, start=datetime(2026, 6, 15, 12, 0)):
        self.now = start

    def __call__(self):
        return self.now


def make_app():
    clock = Clock()
    return RepSquad(":memory:", clock=clock, pbkdf2_iterations=1000), clock


def workout(title="Ноги", visibility="private", exercises=None, date="2026-06-15"):
    return {
        "title": title, "visibility": visibility, "date": date,
        "exercises": [{"name": "Присідання зі штангою", "sets": [{"reps": 5, "weight_kg": 100}]}]
        if exercises is None else exercises,
    }


def lift(name, *sets):
    return {"name": name, "sets": [{"reps": r, "weight_kg": w} for r, w in sets]}


class Api:
    """Test adapter: the old `handle(method, path, query, body, token) -> (status, json)` shape on top of FastAPI.

    Requests go through FastAPI's TestClient, i.e. the real ASGI application (routing, dependencies, validation,
    error handlers), only without opening a network socket."""

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
        """Raw response (status, headers, bytes) for binary files and static content."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = self.client.request(method, path, headers=headers, **kwargs)
        return r.status_code, r.headers, r.content
