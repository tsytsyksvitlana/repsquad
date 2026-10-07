"""Starts RepSquad: python3 run.py [port] [--seed]"""
import os
import sys
from pathlib import Path

from backend.server import serve


def load_env(path=Path(__file__).parent / ".env"):
    """Reads KEY=VALUE pairs from .env (e.g. GEMINI_API_KEY); never overrides variables that are already set."""
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


if __name__ == "__main__":
    load_env()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--seed" in sys.argv:
        from seed import seed
        seed("repsquad.db")
    serve(port=int(args[0]) if args else 8000)
