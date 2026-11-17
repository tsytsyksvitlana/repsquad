"""Central configuration: every tunable value lives here.

Defaults are fixed constants; values that make sense to override per deployment (database path, host, port,
Gemini key/model) are read from the environment on every call, so changes to os.environ take effect at once.
"""
import os
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ---------- server ----------
DEFAULT_DB_PATH = "repsquad.db"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

# The React app is built into frontend/dist (npm run build); the server only serves the result.
FRONTEND_DIST = ROOT / "frontend" / "dist"

# ---------- business logic ----------
SESSION_TTL = timedelta(days=30)
PAGE_MAX = 50
PBKDF2_ITERATIONS = 200_000

# ---------- HTTP caching (seconds) ----------
AVATAR_MAX_AGE = 31536000  # avatar URLs are versioned, so browsers may cache them "forever"
POST_IMAGE_MAX_AGE = 3600

# ---------- Gemini ----------
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODELS = ("gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite")  # primary model + fallbacks
GEMINI_TIMEOUT = 40


def db_path() -> str:
    return os.environ.get("REPSQUAD_DB") or DEFAULT_DB_PATH


def host() -> str:
    return os.environ.get("REPSQUAD_HOST") or DEFAULT_HOST


def port() -> int:
    raw = os.environ.get("REPSQUAD_PORT")
    if not raw:
        return DEFAULT_PORT
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"REPSQUAD_PORT must be an integer, got {raw!r}") from None


def gemini_key() -> str:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""


def gemini_models() -> list[str]:
    """The model from GEMINI_MODEL, or the default list: the next one is tried when a model is overloaded."""
    override = os.environ.get("GEMINI_MODEL")
    return [override] if override else list(GEMINI_MODELS)
