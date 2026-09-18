"""
Suivi de la progression des quêtes — un compteur par (joueur, métrique,
période, clé de période). Incrémenté depuis les points d'action concernés
(ouverture de pack, échange conclu, cadeau envoyé, recyclage, demande d'ami).
La remise à zéro est implicite : une nouvelle période a une nouvelle clé,
donc un nouveau compteur qui part de 0.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quest import QuestProgress


def daily_key(now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    return now.strftime("%Y-%m-%d")


def weekly_key(now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    iso = now.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


async def increment(session: AsyncSession, user_id: int, metric: str, amount: int = 1) -> None:
    if amount <= 0:
        return
    now = datetime.utcnow()
    for period, key in (("daily", daily_key(now)), ("weekly", weekly_key(now))):
        row = await session.get(QuestProgress, (user_id, metric, period, key))
        if not row:
            row = QuestProgress(user_id=user_id, metric=metric, period=period, period_key=key, count=0)
        row.count += amount
        session.add(row)
    # Objectifs de guilde (import tardif : guilds importe ce module).
    from app.services import guilds
    await guilds.track(session, user_id, metric, amount)


async def get_count(session: AsyncSession, user_id: int, metric: str, period: str, period_key: str) -> int:
    row = await session.get(QuestProgress, (user_id, metric, period, period_key))
    return row.count if row else 0
