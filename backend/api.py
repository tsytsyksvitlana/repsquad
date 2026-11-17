"""RepSquad REST API on FastAPI.

create_app() assembles the application from the business-logic object (RepSquad), so tests can build an
isolated instance with an in-memory database. Routes live in backend/routes, one module per domain.
Interactive documentation is available at /docs.
"""
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as HTTPError

from .config import FRONTEND_DIST
from .errors import AppError
from .routes import ai, auth, posts, static, users, workouts
from .routes.deps import Session, make_current
from .services import RepSquad

__all__ = ["FRONTEND_DIST", "Session", "create_app"]


def create_app(service: RepSquad, *, ai_chat=None, static_dir=FRONTEND_DIST) -> FastAPI:
    app = FastAPI(title="RepSquad API", version="2.0",
                  description="Соціальна мережа для спортсменів: тренування, дописи, рекорди, AI-тренер.")
    app.state.ai_chat = ai_chat

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

    me = Depends(make_current(service))
    for module in (auth, users, workouts, posts, ai):
        app.include_router(module.build(service, me))
    # registered last, so the SPA catch-all never shadows the API
    app.include_router(static.build(Path(static_dir).resolve()))
    return app
