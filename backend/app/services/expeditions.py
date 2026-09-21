"""
Expéditions : des équipes de 1 à 3 cartes partent en mission chronométrée et
reviennent avec un butin qui dépend de la durée et de leur puissance cumulée.
Le butin est tiré au départ ; les cartes sont bloquées (ni recyclage, ni
échange, ni cadeau, ni vente) tant que l'expédition n'est pas récupérée.
"""

import random
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.activity import Expedition
from app.models.booster import Booster, BoosterSet
from app.models.card import UserCard
from app.models.message import Message
from app.models.social import TradeListing
from app.models.trade_session import ACTIVE_STATUSES, TradeSession, TradeSessionItem
from app.models.user import User
from app.services import activities_config, booster_inventory, guilds, quest_progress
from app.services.card_generator import CardGeneratorService
from app.services.card_view import build_card_response
from app.services.power import roll_drawn_power
from app.services.ranking import refresh_all_best_ranks
from app.services.wallet import apply_delta
from app.services import unlocks

ON_EXPEDITION = "Cette carte est partie en expédition : récupère l'expédition d'abord."


async def locked_card_ids(session: AsyncSession, card_ids: list[str] | None = None) -> set[str]:
    """Cartes actuellement en expédition (non récupérée), parmi `card_ids` si fourni."""
    rows = (await session.execute(
        select(Expedition.card_ids).where(Expedition.claimed_at.is_(None))
    )).scalars().all()
    locked = {cid for ids in rows for cid in ids}
    return locked & set(card_ids) if card_ids is not None else locked


async def ensure_not_on_expedition(session: AsyncSession, card_ids: list[str]) -> None:
    if await locked_card_ids(session, list(card_ids)):
        raise HTTPException(409, ON_EXPEDITION)


async def _busy_card_ids(session: AsyncSession, user_id: int) -> set[str]:
    """Cartes déjà engagées ailleurs : échange en cours, annonce de vitrine, cadeau non récupéré."""
    in_trades = (await session.execute(
        select(TradeSessionItem.user_card_id)
        .join(TradeSession, TradeSession.id == TradeSessionItem.session_id)
        .where(TradeSessionItem.owner_id == user_id, TradeSession.status.in_(ACTIVE_STATUSES))
    )).scalars().all()
    listed = (await session.execute(
        select(TradeListing.user_card_id).where(TradeListing.user_id == user_id)
    )).scalars().all()
    gifted = (await session.execute(
        select(Message.reward_card_id).where(
            Message.sender_user_id == user_id, Message.claimed_at.is_(None), Message.reward_card_id.is_not(None),
        )
    )).scalars().all()
    return {cid for cid in [*in_trades, *listed, *gifted] if cid}


def _power_factor(total_power: int, cfg: dict) -> float:
    exp = cfg["expeditions"]
    return 1.0 + min(exp["max_power_factor"] - 1.0, total_power / max(1, exp["power_scale"]))


def estimate(duration: int, total_power: int, cfg: dict) -> dict:
    """Butin attendu (pièces, poussière) et chances de booster / carte rare."""
    exp = cfg["expeditions"]
    factor = _power_factor(total_power, cfg)
    coins = round(exp["coins_per_minute"] * duration * factor)
    return {
        "coins": coins,
        "dust": round(coins * exp["dust_ratio"]),
        "booster_chance": min(0.9, exp["booster_chance"].get(str(duration), 0) * factor),
        "rare_card_chance": min(0.5, exp["rare_card_chance"].get(str(duration), 0) * factor),
        "power_factor": round(factor, 2),
    }


async def _out(session: AsyncSession, exp: Expedition, cfg: dict) -> dict:
    now = datetime.utcnow()
    cards = []
    for cid in exp.card_ids:
        card = await session.get(UserCard, cid)
        if card:
            cards.append(await build_card_response(session, card))
    done = now >= exp.ends_at
    return {
        "id": exp.id, "slot": exp.slot, "duration_minutes": exp.duration_minutes,
        "started_at": exp.started_at, "ends_at": exp.ends_at,
        "remaining_seconds": max(0, int((exp.ends_at - now).total_seconds())),
        "done": done, "total_power": exp.total_power, "cards": cards,
        "estimate": estimate(exp.duration_minutes, exp.total_power, cfg),
    }


async def overview(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    active = (await session.execute(
        select(Expedition).where(Expedition.user_id == user.id, Expedition.claimed_at.is_(None))
    )).scalars().all()
    by_slot = {e.slot: e for e in active}
    slots = []
    slot_count = unlocks.expedition_slots(cfg, await unlocks.level_of(session, user)) \
        + (await guilds.level_perks(session, user.id))["extra_expedition_slots"]
    for slot in range(slot_count):
        exp = by_slot.get(slot)
        slots.append({"slot": slot, "expedition": await _out(session, exp, cfg) if exp else None})
    return {
        "slots": slots,
        "durations": cfg["expeditions"]["durations"],
        "max_cards": cfg["expeditions"]["max_cards"],
        "locked_card_ids": sorted({cid for e in active for cid in e.card_ids}),
    }


async def start(session: AsyncSession, user: User, slot: int, duration: int, card_ids: list[str]) -> dict:
    cfg = await activities_config.get_config(session)
    exp_cfg = cfg["expeditions"]
    slot_count = unlocks.expedition_slots(cfg, await unlocks.level_of(session, user)) \
        + (await guilds.level_perks(session, user.id))["extra_expedition_slots"]
    if not 0 <= slot < slot_count:
        raise HTTPException(400, "Emplacement d'expédition invalide.")
    if duration not in exp_cfg["durations"]:
        raise HTTPException(400, "Durée d'expédition invalide.")
    card_ids = list(dict.fromkeys(card_ids))
    if not 1 <= len(card_ids) <= exp_cfg["max_cards"]:
        raise HTTPException(400, f"Envoie entre 1 et {exp_cfg['max_cards']} cartes.")

    busy_slot = (await session.execute(
        select(Expedition.id).where(
            Expedition.user_id == user.id, Expedition.slot == slot, Expedition.claimed_at.is_(None),
        )
    )).first()
    if busy_slot:
        raise HTTPException(409, "Cet emplacement est déjà occupé.")

    cards = (await session.execute(
        select(UserCard).where(UserCard.id.in_(card_ids), UserCard.user_id == user.id)
    )).scalars().all()
    if len(cards) != len(card_ids):
        raise HTTPException(404, "Une des cartes est introuvable ou ne t'appartient pas.")
    await ensure_not_on_expedition(session, card_ids)
    if await _busy_card_ids(session, user.id) & set(card_ids):
        raise HTTPException(409, "Une des cartes est déjà dans un échange, une annonce ou un cadeau en attente.")

    total_power = sum(c.power or 0 for c in cards)
    est = estimate(duration, total_power, cfg)
    loot_bonus = await guilds.buff_value(session, user.id, "expedition_loot")
    if loot_bonus:
        est["coins"] = round(est["coins"] * loot_bonus)
        est["dust"] = round(est["dust"] * loot_bonus)
    now = datetime.utcnow()
    exp = Expedition(
        user_id=user.id, slot=slot, duration_minutes=duration, card_ids=card_ids, total_power=total_power,
        started_at=now, ends_at=now + timedelta(minutes=duration),
        loot={
            "coins": est["coins"], "dust": est["dust"],
            "booster": random.random() < est["booster_chance"],
            "rare_card": random.random() < est["rare_card_chance"],
        },
    )
    session.add(exp)
    await session.commit()
    await session.refresh(exp)
    return await _out(session, exp, cfg)


async def _generate_rare_card(session: AsyncSession, user: User, booster: Booster) -> UserCard | None:
    """Une carte rare ou mieux, tirée dans les sets du booster de récompense."""
    set_ids = (await session.execute(
        select(BoosterSet.set_id).where(BoosterSet.booster_id == booster.id)
    )).scalars().all() or [booster.set_id]
    [data] = await CardGeneratorService().generate_pack(
        session, list(set_ids), cards_count=1, guaranteed_rare=False, force_min_rarity_id="rare",
    ) or [None]
    if not data:
        return None
    card = UserCard(
        user_id=user.id, character_id=data["character_id"], set_id=data["set_id"],
        rarity_id=data["rarity_id"], quality_id=data["quality_id"], specialty_id=data["specialty_id"],
        jewelry_id=data["jewelry_id"], booster_id=booster.id, drop_probability=data["drop_probability"],
        power=roll_drawn_power(data),
    )
    session.add(card)
    user.total_cards += 1
    await session.flush()
    return card


async def claim(session: AsyncSession, user: User, expedition_id: int) -> dict:
    exp = (await session.execute(
        select(Expedition).where(Expedition.id == expedition_id).with_for_update()
    )).scalar_one_or_none()
    if not exp or exp.user_id != user.id:
        raise HTTPException(404, "Expédition introuvable.")
    if exp.claimed_at:
        raise HTTPException(409, "Butin déjà récupéré.")
    if datetime.utcnow() < exp.ends_at:
        raise HTTPException(400, "L'expédition n'est pas encore revenue.")

    cfg = await activities_config.get_config(session)
    loot = exp.loot or {}
    reward = {"coins": int(loot.get("coins", 0)), "dust": int(loot.get("dust", 0)),
              "booster_id": None, "booster_name": None, "card": None}
    if reward["coins"]:
        await apply_delta(session, user, "coins", reward["coins"])
    if reward["dust"]:
        await apply_delta(session, user, "dust", reward["dust"])

    booster = await session.get(Booster, cfg["reward_booster_id"])
    if loot.get("booster") and booster:
        await booster_inventory.grant(session, user.id, booster.id, 1)
        reward["booster_id"], reward["booster_name"] = booster.id, booster.name
    if loot.get("rare_card") and booster:
        card = await _generate_rare_card(session, user, booster)
        if card:
            reward["card"] = await build_card_response(session, card)
            await refresh_all_best_ranks(session)

    exp.claimed_at = datetime.utcnow()
    session.add(exp)
    await quest_progress.increment(session, user.id, "expeditions_completed", 1)
    session.add(user)
    await session.commit()
    return reward
