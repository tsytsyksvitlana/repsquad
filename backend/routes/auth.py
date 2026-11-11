from fastapi import APIRouter

from ..schemas import LoginIn, RegisterIn
from ..services import RepSquad
from .deps import Session


def build(service: RepSquad, me) -> APIRouter:
    router = APIRouter(tags=["auth"])

    @router.get("/api/health")
    def health():
        return {"status": "ok"}

    @router.post("/api/auth/register", status_code=201)
    def register(body: RegisterIn):
        user, token = service.register(body.username, body.password, body.display_name)
        return {"user": user, "token": token}

    @router.post("/api/auth/login")
    def login(body: LoginIn):
        user, token = service.login(body.username, body.password)
        return {"user": user, "token": token}

    @router.post("/api/auth/logout")
    def logout(s: Session = me):
        service.logout(s.token)
        return {"ok": True}

    return router
