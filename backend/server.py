"""Entry point of the web server: FastAPI application served by uvicorn."""
import logging

import uvicorn

from . import config
from .api import create_app
from .services import RepSquad

logger = logging.getLogger("repsquad")


def serve(host=None, port=None, db_path=None):
    if not logging.getLogger().handlers:  # keep the messages on the console unless logging is already configured
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    host = host or config.host()
    port = config.port() if port is None else port
    db_path = db_path or config.db_path()
    service = RepSquad(db_path)
    app = create_app(service)
    # YouTube embeds do not play on an IP-address origin, so users are pointed to "localhost"
    shown = "localhost" if host == "127.0.0.1" else host
    logger.info(f"RepSquad запущено: http://{shown}:{port}   (документація API: /docs, база даних: {db_path}, Ctrl+C для зупинки)")
    try:
        uvicorn.run(app, host=host, port=port, log_level="warning")
    except KeyboardInterrupt:
        logger.info("\nЗупинено.")
    finally:
        service.close()
