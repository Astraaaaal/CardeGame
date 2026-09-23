"""
Attribution des distinctions (badges accordés). Tout passe par ici pour que
l'attribution reste idempotente : donner deux fois le même badge ne crée pas
de doublon et ne change pas la date d'obtention.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.distinction import BETA_TESTER_ID, FOUNDER_ID, Distinction, UserDistinction

logger = logging.getLogger("app")

# Distinctions posées par le jeu. Créées au démarrage si elles manquent ;
# le nom, la couleur et la description restent modifiables depuis l'admin.
_BUILT_IN = (
    {
        "id": BETA_TESTER_ID,
        "name": "Bêta testeur",
        "description": "A joué à la première bêta, avant la remise à zéro.",
        "color": "#b08d57",
        "sort_order": 10,
    },
    {
        "id": FOUNDER_ID,
        "name": "Fondateur",
        "description": "A soutenu le jeu pendant la bêta.",
        "color": "#f0c27b",
        "sort_order": 0,
    },
)


async def seed_built_in(session: AsyncSession) -> None:
    """Crée les distinctions du jeu si elles n'existent pas. Ne touche à rien
    d'autre : une distinction déjà en base garde le nom et la couleur qu'on lui
    a donnés depuis l'admin."""
    existing = set((await session.execute(select(Distinction.id))).scalars().all())
    for row in _BUILT_IN:
        if row["id"] not in existing:
            session.add(Distinction(**row))


async def grant(session: AsyncSession, user_id: int, distinction_id: str,
                reason: str | None = None) -> bool:
    """Donne une distinction à un joueur. Renvoie False si elle l'avait déjà.
    Ne commit pas : l'appelant décide du périmètre de la transaction."""
    already = await session.get(UserDistinction, (user_id, distinction_id))
    if already:
        return False
    session.add(UserDistinction(user_id=user_id, distinction_id=distinction_id, reason=reason))
    return True


async def grant_many(session: AsyncSession, user_ids: list[int], distinction_id: str,
                     reason: str | None = None) -> int:
    """Attribution en masse (réouverture, événement). Renvoie le nombre de
    joueurs qui l'ont réellement reçue — ceux qui l'avaient déjà sont ignorés."""
    if not user_ids:
        return 0
    held = set((await session.execute(
        select(UserDistinction.user_id).where(
            UserDistinction.distinction_id == distinction_id,
            UserDistinction.user_id.in_(user_ids),  # type: ignore[attr-defined]
        )
    )).scalars().all())
    fresh = [uid for uid in user_ids if uid not in held]
    session.add_all(
        UserDistinction(user_id=uid, distinction_id=distinction_id, reason=reason) for uid in fresh
    )
    return len(fresh)


async def for_user(session: AsyncSession, user_id: int) -> list[Distinction]:
    """Distinctions actives portées par un joueur, dans l'ordre d'affichage."""
    rows = (await session.execute(
        select(Distinction)
        .join(UserDistinction, UserDistinction.distinction_id == Distinction.id)  # type: ignore[arg-type]
        .where(UserDistinction.user_id == user_id, Distinction.active.is_(True))  # type: ignore[attr-defined]
        .order_by(Distinction.sort_order, Distinction.name)  # type: ignore[arg-type]
    )).scalars().all()
    return list(rows)
