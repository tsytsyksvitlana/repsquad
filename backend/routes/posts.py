from fastapi import APIRouter
from fastapi.responses import Response

from .. import config
from ..schemas import CommentIn, PostIn, PostPatch
from ..services import RepSquad
from .deps import Session, dump


def build(service: RepSquad, me) -> APIRouter:
    router = APIRouter(tags=["posts"])

    @router.post("/api/posts", status_code=201)
    def create_post(body: PostIn, s: Session = me):
        return service.create_post(s.user_id, dump(body))

    @router.get("/api/posts/{pid:int}")
    def get_post(pid: int, s: Session = me):
        return service.get_post(pid, s.user_id)

    @router.patch("/api/posts/{pid:int}")
    def update_post(pid: int, body: PostPatch, s: Session = me):
        return service.update_post(pid, s.user_id, dump(body))

    @router.delete("/api/posts/{pid:int}")
    def delete_post(pid: int, s: Session = me):
        service.delete_post(pid, s.user_id)
        return {"ok": True}

    @router.get("/api/posts/{pid:int}/image")
    def post_image(pid: int, s: Session = me):
        mime, data = service.get_post_image(pid, s.user_id)
        return Response(data, media_type=mime,
                        headers={"Cache-Control": f"private, max-age={config.POST_IMAGE_MAX_AGE}"})

    @router.post("/api/posts/{pid:int}/like")
    def like_post(pid: int, s: Session = me):
        return service.toggle_post_like(pid, s.user_id)

    @router.post("/api/posts/{pid:int}/comments", status_code=201)
    def add_post_comment(pid: int, body: CommentIn, s: Session = me):
        return {"comments": service.add_post_comment(pid, s.user_id, body.body)}

    @router.delete("/api/post-comments/{cid:int}")
    def delete_post_comment(cid: int, s: Session = me):
        return {"comments": service.delete_post_comment(cid, s.user_id)}

    return router
