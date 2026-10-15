"""Entry point of the web server: FastAPI application served by uvicorn."""
import uvicorn

from .api import create_app
from .services import RepSquad


def serve(host="127.0.0.1", port=8000, db_path="repsquad.db"):
    app = create_app(RepSquad(db_path))
    # YouTube embeds do not play on an IP-address origin, so users are pointed to "localhost"
    shown = "localhost" if host == "127.0.0.1" else host
    print(f"RepSquad запущено: http://{shown}:{port}   (документація API: /docs, база даних: {db_path}, Ctrl+C для зупинки)")
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        print("\nЗупинено.")
