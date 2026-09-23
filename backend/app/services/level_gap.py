"""
Écart de niveau maximum entre deux joueurs pour tout transfert : échange,
achat d'une annonce, cadeau. Empêche qu'un compte avancé équipe un compte
neuf (deuxième compte, ferme à cadeaux) sans pour autant interdire de jouer
avec des amis un peu moins avancés.

L'écart toléré est proportionnel au plus haut des deux niveaux (réglages
« level_gap ») : 30 % par défaut, avec un plancher qui laisse respirer le
début de jeu. La taxe (cf. trade_tax.py) freine la valeur transférée, cet
écart borne la différence de progression — les deux se complètent.
"""

import math

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services import activities_config, unlocks


def max_gap(cfg: dict, top_level: int) -> int:
    """Écart toléré pour deux joueurs dont le plus haut niveau est `top_level`."""
    rules = cfg["level_gap"]
    return max(int(rules["min_gap"]), math.floor(top_level * float(rules["ratio"])))


def gap_of(cfg: dict, level_a: int, level_b: int) -> tuple[int, int]:
    """(écart réel, écart toléré) entre deux niveaux déjà connus."""
    return abs(level_a - level_b), max_gap(cfg, max(level_a, level_b))


def ok_of(cfg: dict, level_a: int, level_b: int) -> bool:
    """Transfert autorisé entre deux niveaux déjà connus."""
    gap, limit = gap_of(cfg, level_a, level_b)
    return gap <= limit


async def between(session: AsyncSession, a: User, b: User) -> tuple[int, int]:
    """(écart réel, écart toléré) entre deux joueurs."""
    cfg = await activities_config.get_config(session)
    return gap_of(cfg, await unlocks.level_of(session, a), await unlocks.level_of(session, b))


def reason(gap: int, limit: int) -> str:
    return f"Écart de niveau trop grand : {gap} niveaux d'écart, {limit} au maximum."


async def require(session: AsyncSession, a: User, b: User, refusal: str) -> None:
    """403 si l'écart de niveau interdit ce transfert. `refusal` : phrase ajoutée au message."""
    gap, limit = await between(session, a, b)
    if gap > limit:
        raise HTTPException(403, f"{reason(gap, limit)} {refusal}")
