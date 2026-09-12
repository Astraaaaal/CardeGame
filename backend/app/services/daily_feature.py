"""
Rotation automatique du "booster du jour" — calculée à la demande (pas de
tâche planifiée). Un admin peut épingler une offre précise pour une date
donnée (DailyFeature) ; sans épingle, on tourne dans le pool `is_daily_pool`.
"""

from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.economy import ShopOffer, DailyFeature


async def get_todays_featured_offer_id(session: AsyncSession, day: Optional[date] = None) -> Optional[str]:
    day = day or date.today()

    pinned = await session.get(DailyFeature, day)
    if pinned:
        return pinned.offer_id

    pool = (await session.execute(
        select(ShopOffer.id)
        .where(ShopOffer.is_daily_pool == True, ShopOffer.active == True)  # noqa: E712
        .order_by(ShopOffer.id)
    )).scalars().all()
    if not pool:
        return None

    return pool[day.toordinal() % len(pool)]
