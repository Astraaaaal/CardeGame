"""
Jeu fermé (pause entre deux versions) : connexion, inscription et toutes les
routes joueur sont refusées, sauf pour l'admin (en-tête X-Admin-Key valide).
L'état vit dans GameConfig et est mis en cache quelques secondes : il est
consulté à chaque requête authentifiée.
"""

import time

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import is_admin_key
from app.models.game_config import GameConfig

DEFAULT_CLOSED_MESSAGE = (
    "La bêta 2.0 ouvre mercredi 23 septembre à 17 h. "
    "Les comptes repartent de zéro, mais personne ne repart les mains vides : "
    "celles et ceux qui ont joué à la première bêta retrouveront un cadeau en arrivant. "
    "À tout à l'heure !"
)

_CACHE_TTL_S = 5.0
_cache: dict = {"at": 0.0, "value": None}


def invalidate() -> None:
    _cache["at"] = 0.0


async def get_status(session: AsyncSession) -> dict:
    if _cache["value"] is not None and time.monotonic() - _cache["at"] < _CACHE_TTL_S:
        return _cache["value"]
    config = await session.get(GameConfig, 1)
    value = {
        "closed": bool(config and config.game_closed),
        "message": (config.closed_message if config and config.closed_message else DEFAULT_CLOSED_MESSAGE),
    }
    _cache.update(at=time.monotonic(), value=value)
    return value


async def ensure_open(session: AsyncSession, admin_key: str = "") -> None:
    """503 « game_closed » si le jeu est fermé et que la requête ne vient pas de l'admin."""
    state = await get_status(session)
    if state["closed"] and not is_admin_key(admin_key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "game_closed", "message": state["message"]},
        )
