"""
Logging — configuration centralisée (remplace les print() épars).

Sortie sur stdout uniquement : Render capture stdout/stderr nativement dans
son tableau de bord de logs, et le disque d'une instance est de toute façon
éphémère (redéploiement = disque neuf), donc pas d'intérêt à écrire dans des
fichiers ici.
"""

import logging
import sys

from app.config import settings

logger = logging.getLogger("app")


def setup_logging() -> None:
    level = logging.INFO if settings.is_production else logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    # Les libs tierces sont bruyantes en DEBUG (requêtes SQL, handshakes...) —
    # gardées à WARNING pour ne pas noyer les logs applicatifs.
    for noisy in ("sqlalchemy.engine", "httpx", "httpcore", "uvicorn.access", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
