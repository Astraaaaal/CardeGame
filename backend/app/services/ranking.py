"""
Rang au classement global de puissance (cf. app/api/leaderboard.py) et
meilleur rang atteint (User.best_global_rank).

Le rang d'un joueur dépend aussi des autres : dès qu'une puissance change
quelque part (ouverture, achat, échange, cadeau, recyclage, suppression de
compte...), on recalcule le rang de TOUS les joueurs en une requête et on
retient chaque amélioration — le meilleur rang est donc exact.
Coût proportionnel au nombre de joueurs possédant des cartes : si ça devient
lourd, passer à un recalcul périodique (toutes les X minutes).

Classement "sportif" : ex-aequo = même rang, le suivant saute (1, 2, 2, 4).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.models.card import UserCard
from app.models.user import User
from app.services.levels import get_total_power


async def current_global_rank(session: AsyncSession, user_id: int) -> int | None:
    """1 + nombre de joueurs strictement plus puissants ; None sans puissance."""
    total = await get_total_power(session, user_id)
    if total <= 0:
        return None
    totals = (
        select(func.sum(UserCard.power).label("total"))
        .where(UserCard.power != None)  # noqa: E711
        .group_by(UserCard.user_id)
        .subquery()
    )
    higher = (await session.execute(
        select(func.count()).select_from(totals).where(totals.c.total > total)
    )).scalar() or 0
    return int(higher) + 1


def record_rank(user: User, rank: int | None) -> bool:
    """Met à jour le meilleur rang si `rank` est meilleur. Ne commit pas."""
    if rank is None or (user.best_global_rank is not None and rank >= user.best_global_rank):
        return False
    user.best_global_rank = rank
    return True


async def refresh_all_best_ranks(session: AsyncSession) -> None:
    """Recalcule le rang de chaque joueur et retient les améliorations. Ne commit pas."""
    total = func.sum(UserCard.power)
    rows = (await session.execute(
        select(UserCard.user_id, total)
        .where(UserCard.power != None)  # noqa: E711
        .group_by(UserCard.user_id)
        .order_by(total.desc())
    )).all()

    ranks: dict[int, int] = {}
    previous_total = None
    rank = 0
    for position, (user_id, user_total) in enumerate(rows, start=1):
        user_total = int(user_total or 0)
        if user_total <= 0:
            break
        if user_total != previous_total:
            rank = position
            previous_total = user_total
        ranks[user_id] = rank
    if not ranks:
        return

    users = (await session.execute(select(User).where(User.id.in_(ranks.keys())))).scalars().all()
    for user in users:
        if record_rank(user, ranks[user.id]):
            session.add(user)
