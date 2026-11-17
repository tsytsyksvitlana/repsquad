from fastapi import APIRouter
from fastapi.responses import Response

from .. import config
from ..schemas import ImageIn, ProfileIn
from ..services import RepSquad
from .deps import Session, dump


def build(service: RepSquad, me) -> APIRouter:
    router = APIRouter()

    # ---------- profile ----------
    @router.get("/api/me", tags=["profile"])
    def get_me(s: Session = me):
        return service.get_my_profile(s.user_id)

    @router.patch("/api/me", tags=["profile"])
    def update_me(body: ProfileIn, s: Session = me):
        return service.update_profile(s.user_id, dump(body))

    @router.put("/api/me/avatar", tags=["profile"])
    def set_avatar(body: ImageIn, s: Session = me):
        return service.set_avatar(s.user_id, body.image)

    @router.delete("/api/me/avatar", tags=["profile"])
    def delete_avatar(s: Session = me):
        return service.delete_avatar(s.user_id)

    @router.get("/api/me/records", tags=["records"])
    def records(s: Session = me):
        return {"items": service.records(s.user_id)}

    @router.get("/api/me/progress", tags=["records"])
    def progress(exercise: str | None = None, s: Session = me):
        return service.progress(s.user_id, exercise)

    @router.get("/api/exercises", tags=["records"])
    def exercises(s: Session = me):
        return {"items": service.exercise_names(s.user_id)}

    # ---------- other users ----------
    @router.get("/api/users", tags=["users"])
    def search_users(q: str | None = None, s: Session = me):
        return {"items": service.search_users(q, s.user_id)}

    @router.get("/api/users/{username}", tags=["users"])
    def profile(username: str, s: Session = me):
        return service.get_profile(username, s.user_id)

    @router.post("/api/users/{username}/follow", tags=["users"])
    def follow(username: str, s: Session = me):
        return service.follow(s.user_id, username)

    @router.delete("/api/users/{username}/follow", tags=["users"])
    def unfollow(username: str, s: Session = me):
        return service.unfollow(s.user_id, username)

    @router.get("/api/users/{username}/avatar", tags=["users"])
    def avatar(username: str):
        # <img> tags cannot send an Authorization header, so pictures are public; the URL is versioned.
        mime, data = service.get_avatar(username)
        return Response(data, media_type=mime,
                        headers={"Cache-Control": f"public, max-age={config.AVATAR_MAX_AGE}, immutable"})

    def user_items(username, limit, offset, visibility, kind, default_kind, s):
        return service.user_workouts(username, s.user_id, limit, offset, visibility, kind or default_kind)

    @router.get("/api/users/{username}/workouts", tags=["users"])
    def user_workouts(username: str, limit: str | None = None, offset: str | None = None,
                      visibility: str | None = None, kind: str | None = None, s: Session = me):
        return user_items(username, limit, offset, visibility, kind, "workouts", s)

    @router.get("/api/users/{username}/timeline", tags=["users"])
    def user_timeline(username: str, limit: str | None = None, offset: str | None = None,
                      visibility: str | None = None, kind: str | None = None, s: Session = me):
        return user_items(username, limit, offset, visibility, kind, "all", s)

    return router
