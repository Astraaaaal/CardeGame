"""
Atelier à clics : chaque tap remplit une jauge ; une jauge pleine rapporte des
pièces (parfois de la poussière) et un fragment de booster, 10 fragments donnant
un booster. Le serveur ne compte que `max_taps_per_second` taps par seconde
écoulée et plafonne les jauges par jour : un auto-clicker ne rapporte pas plus
qu'un humain rapide.
"""

import random
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booster import Booster
from app.models.user import User
from app.services import activities_config, booster_inventory, guilds, quest_progress
from app.services.presence_bonus import get_activity
from app.services.wallet import apply_delta

# Taps « en réserve » acceptés au plus après une pause (évite d'accumuler du
# crédit de vitesse en restant inactif puis d'envoyer une rafale).
_MAX_ELAPSED_S = 3


def _state(row, cfg: dict, gauges_per_day: int | None = None) -> dict:
    ws = cfg["workshop"]
    return {
        "taps": row.workshop_taps,
        "taps_per_gauge": ws["taps_per_gauge"],
        "gauges_today": row.workshop_gauges_today,
        "gauges_per_day": gauges_per_day or ws["gauges_per_day"],
        "fragments": row.workshop_fragments,
        "fragments_per_booster": ws["fragments_per_booster"],
        "coins_per_gauge": ws["coins_per_gauge"],
    }


def _roll_day(row) -> None:
    today = datetime.utcnow().date()
    if row.workshop_day != today:
        row.workshop_day = today
        row.workshop_gauges_today = 0


async def status(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    row = await get_activity(session, user.id)
    _roll_day(row)
    session.add(row)
    await session.commit()
    return _state(row, cfg, await _daily_cap(session, user, cfg))


async def _daily_cap(session: AsyncSession, user: User, cfg: dict) -> int:
    """Jauges par jour, relevées par le bonus de guilde « atelier »."""
    extra = await guilds.buff_value(session, user.id, "workshop")
    return cfg["workshop"]["gauges_per_day"] + int(extra or 0)


async def tap(session: AsyncSession, user: User, count: int) -> dict:
    cfg = await activities_config.get_config(session)
    ws = cfg["workshop"]
    cap = await _daily_cap(session, user, cfg)
    row = await get_activity(session, user.id)
    _roll_day(row)
    now = datetime.utcnow()

    elapsed = (now - row.workshop_last_at).total_seconds() if row.workshop_last_at else 1.0
    allowed = int(ws["max_taps_per_second"] * min(_MAX_ELAPSED_S, max(0.0, elapsed)))
    accepted = max(0, min(count, allowed))
    if row.workshop_gauges_today >= cap:
        accepted = 0
    row.workshop_last_at = now
    row.workshop_taps += accepted

    reward = {"coins": 0, "dust": 0, "gauges": 0, "boosters": 0}
    while row.workshop_taps >= ws["taps_per_gauge"] and row.workshop_gauges_today < cap:
        row.workshop_taps -= ws["taps_per_gauge"]
        row.workshop_gauges_today += 1
        reward["gauges"] += 1
        reward["coins"] += ws["coins_per_gauge"]
        if random.random() < ws["dust_chance"]:
            reward["dust"] += ws["dust_amount"]
        row.workshop_fragments += 1
        if row.workshop_fragments >= ws["fragments_per_booster"]:
            row.workshop_fragments -= ws["fragments_per_booster"]
            reward["boosters"] += 1
    if row.workshop_gauges_today >= cap:
        row.workshop_taps = 0  # plus rien à remplir aujourd'hui

    if reward["gauges"]:
        await quest_progress.increment(session, user.id, "workshop_gauges", reward["gauges"])
    if reward["coins"]:
        await apply_delta(session, user, "coins", reward["coins"])
    if reward["dust"]:
        await apply_delta(session, user, "dust", reward["dust"])
    booster = await session.get(Booster, cfg["reward_booster_id"]) if reward["boosters"] else None
    if booster:
        await booster_inventory.grant(session, user.id, booster.id, reward["boosters"])
    session.add(row)
    await session.commit()
    return {
        **_state(row, cfg, cap), "accepted": accepted, "reward": reward,
        "booster_id": booster.id if booster else None, "booster_name": booster.name if booster else None,
    }
