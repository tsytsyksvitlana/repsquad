from fastapi import APIRouter

from ..schemas import CommentIn, WorkoutIn, WorkoutPatch
from ..services import RepSquad
from .deps import Session, dump


def build(service: RepSquad, me) -> APIRouter:
    router = APIRouter()

    @router.post("/api/workouts", status_code=201, tags=["workouts"])
    def create_workout(body: WorkoutIn, s: Session = me):
        workout, records_ = service.create_workout(s.user_id, dump(body))
        return {"workout": workout, "new_records": records_}

    @router.get("/api/workouts/{wid:int}", tags=["workouts"])
    def get_workout(wid: int, s: Session = me):
        return service.get_workout(wid, s.user_id)

    @router.patch("/api/workouts/{wid:int}", tags=["workouts"])
    def update_workout(wid: int, body: WorkoutPatch, s: Session = me):
        return service.update_workout(wid, s.user_id, dump(body))

    @router.delete("/api/workouts/{wid:int}", tags=["workouts"])
    def delete_workout(wid: int, s: Session = me):
        service.delete_workout(wid, s.user_id)
        return {"ok": True}

    @router.post("/api/workouts/{wid:int}/like", tags=["workouts"])
    def like(wid: int, s: Session = me):
        return service.toggle_like(wid, s.user_id)

    @router.post("/api/workouts/{wid:int}/comments", status_code=201, tags=["workouts"])
    def add_comment(wid: int, body: CommentIn, s: Session = me):
        return {"comments": service.add_comment(wid, s.user_id, body.body)}

    @router.delete("/api/comments/{cid:int}", tags=["workouts"])
    def delete_comment(cid: int, s: Session = me):
        return {"comments": service.delete_comment(cid, s.user_id)}

    # ---------- feed ----------
    @router.get("/api/feed", tags=["feed"])
    def feed(limit: str | None = None, offset: str | None = None, kind: str | None = None, s: Session = me):
        return service.feed(s.user_id, limit, offset, kind or "all")

    @router.get("/api/discover", tags=["feed"])
    def discover(limit: str | None = None, offset: str | None = None, kind: str | None = None, s: Session = me):
        return service.discover(s.user_id, limit, offset, kind or "all")

    return router
