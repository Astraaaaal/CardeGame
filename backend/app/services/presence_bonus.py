"""
Présence : tant que l'appli est affichée, elle envoie un signal toutes les
30 s. La chance de rareté des boosters monte de ×1 à ×max en `full_after_hours`
de présence continue ; une absence de plus de `reset_after_minutes` la remet à
zéro. Pendant l'absence, le coffre se remplit (plafonné), à récupérer au retour.
"""

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity import UserActivity
from app.models.user import User
from app.services import activities_config
from app.services.wallet import apply_delta
from app.services import unlocks


async def get_activity(session: AsyncSession, user_id: int) -> UserActivity:
    row = await session.get(UserActivity, user_id)
    if not row:
        row = UserActivity(user_id=user_id)
        session.add(row)
    return row


def _multiplier(row: UserActivity, cfg: dict, now: datetime, max_multiplier: float) -> float:
    presence = cfg["presence"]
    if max_multiplier <= 1.0 or not row.presence_since or not row.presence_ping_at:
        return 1.0
    if now - row.presence_ping_at > timedelta(minutes=presence["reset_after_minutes"]):
        return 1.0
    ratio = min(1.0, (now - row.presence_since).total_seconds() / (presence["full_after_hours"] * 3600))
    return round(1.0 + (max_multiplier - 1.0) * ratio, 3)


async def _max_for(session: AsyncSession, user: User, cfg: dict) -> float:
    """Maximum selon le niveau (1.0 tant que la chance de présence n'est pas débloquée)."""
    return unlocks.presence_max_multiplier(cfg, await unlocks.level_of(session, user))


async def luck_multiplier(session: AsyncSession, user_id: int) -> float:
    """Bonus de chance de rareté actuel (1.0 = aucun). Utilisé à l'ouverture des boosters."""
    row = await session.get(UserActivity, user_id)
    user = await session.get(User, user_id)
    if not row or not user:
        return 1.0
    cfg = await activities_config.get_config(session)
    return _multiplier(row, cfg, datetime.utcnow(), await _max_for(session, user, cfg))


def _chest_content(row: UserActivity, cfg: dict) -> dict:
    chest = cfg["chest"]
    hours = row.chest_seconds / 3600
    return {
        "coins": int(chest["coins_per_hour"] * hours),
        "dust": int(chest["dust_per_hour"] * hours),
        "hours": round(hours, 2),
        "cap_hours": chest["cap_hours"],
    }


async def status(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    row = await get_activity(session, user.id)
    now = datetime.utcnow()
    presence = cfg["presence"]
    active = bool(
        row.presence_since and row.presence_ping_at
        and now - row.presence_ping_at <= timedelta(minutes=presence["reset_after_minutes"])
    )
    max_multiplier = await _max_for(session, user, cfg)
    return {
        "multiplier": _multiplier(row, cfg, now, max_multiplier),
        "max_multiplier": max_multiplier,
        "unlocked": max_multiplier > 1.0,
        "full_after_hours": presence["full_after_hours"],
        "present_seconds": int((now - row.presence_since).total_seconds()) if active else 0,
        "chest": _chest_content(row, cfg),
    }


async def ping(session: AsyncSession, user: User) -> dict:
    """Signal de présence (appli affichée). Après une absence, la présence
    repart de zéro et le temps d'absence remplit le coffre."""
    cfg = await activities_config.get_config(session)
    row = await get_activity(session, user.id)
    now = datetime.utcnow()
    reset_after = timedelta(minutes=cfg["presence"]["reset_after_minutes"])

    if not row.presence_ping_at or now - row.presence_ping_at > reset_after:
        if row.presence_ping_at:
            away = int((now - row.presence_ping_at).total_seconds())
            cap = int(cfg["chest"]["cap_hours"] * 3600)
            row.chest_seconds = min(cap, row.chest_seconds + away)
        row.presence_since = now
    row.presence_ping_at = now
    session.add(row)
    await session.commit()
    return await status(session, user)


async def claim_chest(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    row = await get_activity(session, user.id)
    content = _chest_content(row, cfg)
    if content["coins"] > 0:
        await apply_delta(session, user, "coins", content["coins"])
    if content["dust"] > 0:
        await apply_delta(session, user, "dust", content["dust"])
    row.chest_seconds = 0
    session.add(row)
    await session.commit()
    return content
