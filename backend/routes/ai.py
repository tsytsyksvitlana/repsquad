from fastapi import APIRouter, Request

from .. import ai
from ..schemas import AiIn
from ..services import RepSquad
from ..videos import video_items
from .deps import Session


def build(service: RepSquad, me) -> APIRouter:
    router = APIRouter(tags=["ai"])

    @router.post("/api/ai/workout")
    def ai_workout(body: AiIn, request: Request, s: Session = me):
        # A plain `def` endpoint runs in a worker thread, so the slow model call never blocks other requests.
        draft = ai.generate_workout(body.prompt, service.profile_for_ai(s.user_id), service.exercise_names(s.user_id),
                                    chat=request.app.state.ai_chat, records=service.records(s.user_id))
        return {"draft": draft}

    @router.get("/api/videos")
    def videos(s: Session = me):
        return {"items": video_items()}

    return router
