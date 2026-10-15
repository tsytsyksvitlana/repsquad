"""RepSquad REST API on FastAPI.

create_app() assembles the application from the business-logic object (RepSquad), so tests can build an
isolated instance with an in-memory database. Interactive documentation is available at /docs.
"""
from pathlib import Path
from typing import NamedTuple
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as HTTPError

from . import ai
from .errors import AppError
from .schemas import (AiIn, CommentIn, ImageIn, LoginIn, PostIn, PostPatch, ProfileIn, RegisterIn, WorkoutIn,
                      WorkoutPatch)
from .services import RepSquad
from .videos import video_items

# The React app is built into frontend/dist (npm run build); the server only serves the result.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class Session(NamedTuple):
    user_id: int
    token: str


def _dump(model):
    """Only the fields the client actually sent (absent fields keep their defaults in the domain layer)."""
    return model.model_dump(exclude_unset=True)


def create_app(service: RepSquad, *, ai_chat=None, static_dir=FRONTEND_DIST) -> FastAPI:
    app = FastAPI(title="RepSquad API", version="2.0",
                  description="Соціальна мережа для спортсменів: тренування, дописи, рекорди, AI-тренер.")
    app.state.ai_chat = ai_chat
    static_root = Path(static_dir).resolve()

    # ---------- errors: one JSON shape {"error": "..."} for every failure ----------
    @app.exception_handler(AppError)
    async def app_error(_: Request, e: AppError):
        return JSONResponse({"error": e.message}, status_code=e.status)

    @app.exception_handler(HTTPError)
    async def http_error(_: Request, e: HTTPError):
        messages = {404: "Маршрут не знайдено", 405: "Метод не підтримується"}
        return JSONResponse({"error": messages.get(e.status_code, str(e.detail))}, status_code=e.status_code)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(_: Request, e: RequestValidationError):
        kinds = {err["type"] for err in e.errors()}
        if "json_invalid" in kinds:
            message = "Некоректний JSON"
        elif kinds & {"model_attributes_type", "dict_type", "missing"}:
            message = "Очікується JSON-об'єкт"
        else:
            field = ".".join(str(p) for p in e.errors()[0]["loc"][1:]) or "запит"
            message = f"Некоректні дані запиту (поле «{field}»)"
        return JSONResponse({"error": message}, status_code=400)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    # ---------- authentication ----------
    def current(authorization: str | None = Header(default=None)) -> Session:
        """Bearer-token dependency: resolves the signed-in user or raises Unauthorized (401)."""
        token = authorization[7:].strip() if authorization and authorization.lower().startswith("bearer ") else None
        return Session(service.authenticate(token), token)

    me = Depends(current)

    @app.get("/api/health", tags=["auth"])
    def health():
        return {"status": "ok"}

    @app.post("/api/auth/register", status_code=201, tags=["auth"])
    def register(body: RegisterIn):
        user, token = service.register(body.username, body.password, body.display_name)
        return {"user": user, "token": token}

    @app.post("/api/auth/login", tags=["auth"])
    def login(body: LoginIn):
        user, token = service.login(body.username, body.password)
        return {"user": user, "token": token}

    @app.post("/api/auth/logout", tags=["auth"])
    def logout(s: Session = me):
        service.logout(s.token)
        return {"ok": True}

    # ---------- profile ----------
    @app.get("/api/me", tags=["profile"])
    def get_me(s: Session = me):
        username = service._one("SELECT username FROM users WHERE id = ?", (s.user_id,))["username"]
        return service.get_profile(username, s.user_id)

    @app.patch("/api/me", tags=["profile"])
    def update_me(body: ProfileIn, s: Session = me):
        return service.update_profile(s.user_id, _dump(body))

    @app.put("/api/me/avatar", tags=["profile"])
    def set_avatar(body: ImageIn, s: Session = me):
        return service.set_avatar(s.user_id, body.image)

    @app.delete("/api/me/avatar", tags=["profile"])
    def delete_avatar(s: Session = me):
        return service.delete_avatar(s.user_id)

    @app.get("/api/me/records", tags=["records"])
    def records(s: Session = me):
        return {"items": service.records(s.user_id)}

    @app.get("/api/me/progress", tags=["records"])
    def progress(exercise: str | None = None, s: Session = me):
        return service.progress(s.user_id, exercise)

    @app.get("/api/exercises", tags=["records"])
    def exercises(s: Session = me):
        return {"items": service.exercise_names(s.user_id)}

    @app.get("/api/users", tags=["users"])
    def search_users(q: str | None = None, s: Session = me):
        return {"items": service.search_users(q, s.user_id)}

    @app.get("/api/users/{username}", tags=["users"])
    def profile(username: str, s: Session = me):
        return service.get_profile(username, s.user_id)

    @app.post("/api/users/{username}/follow", tags=["users"])
    def follow(username: str, s: Session = me):
        return service.follow(s.user_id, username)

    @app.delete("/api/users/{username}/follow", tags=["users"])
    def unfollow(username: str, s: Session = me):
        return service.unfollow(s.user_id, username)

    @app.get("/api/users/{username}/avatar", tags=["users"])
    def avatar(username: str):
        # <img> tags cannot send an Authorization header, so pictures are public; the URL is versioned.
        mime, data = service.get_avatar(username)
        return Response(data, media_type=mime, headers={"Cache-Control": "public, max-age=31536000, immutable"})

    @app.get("/api/users/{username}/workouts", tags=["users"])
    def user_workouts(username: str, limit: str | None = None, offset: str | None = None,
                      visibility: str | None = None, kind: str | None = None, s: Session = me):
        return service.user_workouts(username, s.user_id, limit, offset, visibility, kind or "workouts")

    @app.get("/api/users/{username}/timeline", tags=["users"])
    def user_timeline(username: str, limit: str | None = None, offset: str | None = None,
                      visibility: str | None = None, kind: str | None = None, s: Session = me):
        return service.user_workouts(username, s.user_id, limit, offset, visibility, kind or "all")

    # ---------- workouts ----------
    @app.post("/api/workouts", status_code=201, tags=["workouts"])
    def create_workout(body: WorkoutIn, s: Session = me):
        workout, records_ = service.create_workout(s.user_id, _dump(body))
        return {"workout": workout, "new_records": records_}

    @app.get("/api/workouts/{wid:int}", tags=["workouts"])
    def get_workout(wid: int, s: Session = me):
        return service.get_workout(wid, s.user_id)

    @app.patch("/api/workouts/{wid:int}", tags=["workouts"])
    def update_workout(wid: int, body: WorkoutPatch, s: Session = me):
        return service.update_workout(wid, s.user_id, _dump(body))

    @app.delete("/api/workouts/{wid:int}", tags=["workouts"])
    def delete_workout(wid: int, s: Session = me):
        service.delete_workout(wid, s.user_id)
        return {"ok": True}

    @app.post("/api/workouts/{wid:int}/like", tags=["workouts"])
    def like(wid: int, s: Session = me):
        return service.toggle_like(wid, s.user_id)

    @app.post("/api/workouts/{wid:int}/comments", status_code=201, tags=["workouts"])
    def add_comment(wid: int, body: CommentIn, s: Session = me):
        return {"comments": service.add_comment(wid, s.user_id, body.body)}

    @app.delete("/api/comments/{cid:int}", tags=["workouts"])
    def delete_comment(cid: int, s: Session = me):
        return {"comments": service.delete_comment(cid, s.user_id)}

    # ---------- feed ----------
    @app.get("/api/feed", tags=["feed"])
    def feed(limit: str | None = None, offset: str | None = None, kind: str | None = None, s: Session = me):
        return service.feed(s.user_id, limit, offset, kind or "all")

    @app.get("/api/discover", tags=["feed"])
    def discover(limit: str | None = None, offset: str | None = None, kind: str | None = None, s: Session = me):
        return service.discover(s.user_id, limit, offset, kind or "all")

    # ---------- posts ----------
    @app.post("/api/posts", status_code=201, tags=["posts"])
    def create_post(body: PostIn, s: Session = me):
        return service.create_post(s.user_id, _dump(body))

    @app.get("/api/posts/{pid:int}", tags=["posts"])
    def get_post(pid: int, s: Session = me):
        return service.get_post(pid, s.user_id)

    @app.patch("/api/posts/{pid:int}", tags=["posts"])
    def update_post(pid: int, body: PostPatch, s: Session = me):
        return service.update_post(pid, s.user_id, _dump(body))

    @app.delete("/api/posts/{pid:int}", tags=["posts"])
    def delete_post(pid: int, s: Session = me):
        service.delete_post(pid, s.user_id)
        return {"ok": True}

    @app.get("/api/posts/{pid:int}/image", tags=["posts"])
    def post_image(pid: int, s: Session = me):
        mime, data = service.get_post_image(pid, s.user_id)
        return Response(data, media_type=mime, headers={"Cache-Control": "private, max-age=3600"})

    @app.post("/api/posts/{pid:int}/like", tags=["posts"])
    def like_post(pid: int, s: Session = me):
        return service.toggle_post_like(pid, s.user_id)

    @app.post("/api/posts/{pid:int}/comments", status_code=201, tags=["posts"])
    def add_post_comment(pid: int, body: CommentIn, s: Session = me):
        return {"comments": service.add_post_comment(pid, s.user_id, body.body)}

    @app.delete("/api/post-comments/{cid:int}", tags=["posts"])
    def delete_post_comment(cid: int, s: Session = me):
        return {"comments": service.delete_post_comment(cid, s.user_id)}

    # ---------- AI trainer and videos ----------
    @app.post("/api/ai/workout", tags=["ai"])
    def ai_workout(body: AiIn, request: Request, s: Session = me):
        # A plain `def` endpoint runs in a worker thread, so the slow model call never blocks other requests.
        draft = ai.generate_workout(body.prompt, service.profile_for_ai(s.user_id), service.exercise_names(s.user_id),
                                    chat=request.app.state.ai_chat, records=service.records(s.user_id))
        return {"draft": draft}

    @app.get("/api/videos", tags=["ai"])
    def videos(s: Session = me):
        return {"items": video_items()}

    # ---------- built frontend (registered last, so it never shadows the API) ----------
    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPError(404)
        if not (static_root / "index.html").is_file():
            return JSONResponse({"error": "Frontend is not built. Run: cd frontend && npm install && npm run build"},
                                status_code=503)
        target = (static_root / (unquote(full_path) or "index.html")).resolve()
        if static_root not in target.parents or not target.is_file():  # also blocks path traversal
            return JSONResponse({"error": "Не знайдено"}, status_code=404)
        return FileResponse(target)

    return app
