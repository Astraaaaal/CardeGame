"""
Rang au classement global de puissance (cf. app/api/leaderboard.py) et
suivi du meilleur rang atteint (User.best_global_rank).

Le rang dépend aussi des autres joueurs : on ne le recalcule pas en continu,
seulement quand la puissance du joueur augmente (ouverture de booster,
échange, achat) et quand sa vitrine ou le classement global est consulté.
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


async def refresh_best_rank(session: AsyncSession, user: User) -> None:
    """Recalcule le rang actuel du joueur et le retient s'il est meilleur. Ne commit pas."""
    if record_rank(user, await current_global_rank(session, user.id)):
        session.add(user)
