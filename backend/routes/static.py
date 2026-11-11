from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as HTTPError


def build(static_root: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/{full_path:path}", include_in_schema=False)
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

    return router
