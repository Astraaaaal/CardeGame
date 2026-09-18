"""
Quêtes — assignation (tirage aléatoire parmi les modèles actifs de la
période, une fois par période), progression, récupération de récompense.
"""

import random
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.services import quest_progress
from app.models.quest import QuestDef, UserQuest, DAILY_QUEST_COUNT, WEEKLY_QUEST_COUNT
from app.services.quest_progress import daily_key, weekly_key, get_count
from app.services.wallet import apply_delta
from app.services import booster_inventory

_COUNT_BY_PERIOD = {"daily": DAILY_QUEST_COUNT, "weekly": WEEKLY_QUEST_COUNT}


async def _ensure_assigned(session: AsyncSession, user_id: int, period: str, period_key: str) -> list[UserQuest]:
    existing = (await session.execute(
        select(UserQuest).where(
            UserQuest.user_id == user_id, UserQuest.period == period, UserQuest.period_key == period_key,
        )
    )).scalars().all()
    if existing:
        return existing

    pool = (await session.execute(
        select(QuestDef).where(QuestDef.period == period, QuestDef.active == True)  # noqa: E712
    )).scalars().all()
    if not pool:
        return []

    n = min(_COUNT_BY_PERIOD.get(period, 3), len(pool))
    chosen = random.sample(pool, n)
    rows = [
        UserQuest(user_id=user_id, quest_def_id=q.id, period=period, period_key=period_key)
        for q in chosen
    ]
    session.add_all(rows)
    await session.commit()
    return rows


async def list_quests(session: AsyncSession, user_id: int) -> list[dict]:
    now = datetime.utcnow()
    out = []
    for period, key in (("daily", daily_key(now)), ("weekly", weekly_key(now))):
        assigned = await _ensure_assigned(session, user_id, period, key)
        for uq in assigned:
            qdef = await session.get(QuestDef, uq.quest_def_id)
            if not qdef:
                continue
            progress = await get_count(session, user_id, qdef.metric, period, key)
            out.append({
                "id": uq.id, "quest_def_id": qdef.id, "name": qdef.name, "description": qdef.description,
                "period": period, "threshold": qdef.threshold, "progress": min(progress, qdef.threshold),
                "reward_resource_id": qdef.reward_resource_id, "reward_amount": qdef.reward_amount,
                "reward_booster_id": qdef.reward_booster_id,
                "completed": progress >= qdef.threshold, "claimed_at": uq.claimed_at,
            })
    return out


async def claim_quest(session: AsyncSession, user: User, user_quest_id: int) -> dict:
    uq = await session.get(UserQuest, user_quest_id)
    if not uq or uq.user_id != user.id:
        raise HTTPException(404, "Quête introuvable.")
    if uq.claimed_at:
        raise HTTPException(409, "Récompense déjà récupérée.")

    qdef = await session.get(QuestDef, uq.quest_def_id)
    if not qdef:
        raise HTTPException(404, "Quête introuvable.")

    progress = await get_count(session, user.id, qdef.metric, uq.period, uq.period_key)
    if progress < qdef.threshold:
        raise HTTPException(400, "Quête pas encore terminée.")

    if qdef.reward_resource_id and qdef.reward_amount:
        await apply_delta(session, user, qdef.reward_resource_id, qdef.reward_amount)
    if qdef.reward_booster_id:
        await booster_inventory.grant(session, user.id, qdef.reward_booster_id, 1)

    uq.claimed_at = datetime.utcnow()
    await quest_progress.increment(session, user.id, "quests_completed", 1)
    session.add(uq)
    await session.commit()

    quests = await list_quests(session, user.id)
    return next((q for q in quests if q["id"] == uq.id), {})
