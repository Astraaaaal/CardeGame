"""
Niveaux — dérivés à la volée de la puissance totale (somme de UserCard.power),
comparés à la table de paliers éditable LevelTier. `User.claimed_level`
retient jusqu'où la récompense a déjà été récupérée (le niveau "affiché"
avance tout seul dès que la puissance suffit, indépendamment de la récupération).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.models.user import User
from app.models.card import UserCard
from app.models.level import LevelTier
from app.services.wallet import apply_delta


async def get_total_power(session: AsyncSession, user_id: int) -> int:
    total = (await session.execute(
        select(func.sum(UserCard.power)).where(UserCard.user_id == user_id, UserCard.power != None)  # noqa: E711
    )).scalar()
    return int(total or 0)


async def get_all_tiers(session: AsyncSession) -> list[LevelTier]:
    rows = (await session.execute(select(LevelTier).order_by(LevelTier.level))).scalars().all()
    return rows


def current_level_for_power(tiers: list[LevelTier], total_power: int) -> int:
    """Le plus haut palier dont le seuil est atteint (tiers doit être trié par level croissant)."""
    level = tiers[0].level if tiers else 1
    for tier in tiers:
        if total_power >= tier.power_required:
            level = tier.level
        else:
            break
    return level


async def get_status(session: AsyncSession, user: User) -> dict:
    tiers = await get_all_tiers(session)
    total_power = await get_total_power(session, user.id)
    current_level = current_level_for_power(tiers, total_power)
    next_tier = next((t for t in tiers if t.level > current_level), None)

    pending = [
        t for t in tiers
        if t.level > user.claimed_level and t.level <= current_level
        and t.reward_resource_id and t.reward_amount
    ]

    return {
        "current_level": current_level,
        "total_power": total_power,
        "claimed_level": user.claimed_level,
        "next_level_power_required": next_tier.power_required if next_tier else None,
        "pending_rewards": [
            {"level": t.level, "reward_resource_id": t.reward_resource_id, "reward_amount": t.reward_amount}
            for t in pending
        ],
        "has_unclaimed": bool(pending),
    }


async def claim_level_rewards(session: AsyncSession, user: User) -> dict:
    tiers = await get_all_tiers(session)
    total_power = await get_total_power(session, user.id)
    current_level = current_level_for_power(tiers, total_power)

    pending = [t for t in tiers if t.level > user.claimed_level and t.level <= current_level]
    if not pending:
        return await get_status(session, user)

    for tier in pending:
        if tier.reward_resource_id and tier.reward_amount:
            await apply_delta(session, user, tier.reward_resource_id, tier.reward_amount)

    user.claimed_level = current_level
    session.add(user)
    await session.commit()
    return await get_status(session, user)
