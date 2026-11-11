"""Starts RepSquad: python3 run.py [port] [--seed]"""
import os
import sys
from pathlib import Path

from backend import config
from backend.server import serve


def load_env(path=Path(__file__).parent / ".env"):
    """Reads KEY=VALUE pairs from .env (e.g. GEMINI_API_KEY); never overrides variables that are already set."""
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def parse_port(args):
    """Port from the first positional argument; exits with a clear message when it is not a number."""
    if not args:
        return None  # serve() falls back to config
    try:
        return int(args[0])
    except ValueError:
        sys.exit(f"Invalid port {args[0]!r}: expected a number, e.g. python3 run.py 8000")


if __name__ == "__main__":
    load_env()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    port = parse_port(args)
    if "--seed" in sys.argv:
        from seed import seed
        seed(config.db_path())
    serve(port=port)
