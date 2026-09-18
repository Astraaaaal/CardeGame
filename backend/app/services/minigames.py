"""
Mini-jeux : « plus ou moins » (deviner si la carte suivante est plus ou moins
puissante, gain multiplié à chaque bonne réponse) et roue de la fortune (un
tour gratuit par jour, les suivants en pièces). Mises uniquement en pièces ou
en poussière : jamais la monnaie premium, pour rester hors du cadre des jeux
d'argent. Tout le hasard est tiré côté serveur.
"""

import random
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.activity import HigherLowerGame
from app.models.booster import Booster, BoosterSet
from app.models.card import UserCard
from app.models.user import User
from app.services import activities_config, booster_inventory, reroll_inventory
from app.services.card_generator import CardGeneratorService
from app.services.card_view import build_card_response
from app.services.power import roll_power
from app.services.presence_bonus import get_activity
from app.services.wallet import apply_delta, get_balance

STAKE_RESOURCES = ("coins", "dust")
WHEEL_REROLL_RULES = {
    "reroll_rarity": True, "reroll_quality": False, "reroll_specialty": False,
    "reroll_jewelry": False, "reroll_power": False, "reroll_mode": "guaranteed_min",
}


# ─────────────────────────────  PLUS OU MOINS  ─────────────────────────────

async def _random_card(session: AsyncSession, cfg: dict) -> dict:
    """Carte tirée au hasard dans les sets du booster de récompense (non attribuée)."""
    booster = await session.get(Booster, cfg["reward_booster_id"])
    set_ids = []
    if booster:
        set_ids = (await session.execute(
            select(BoosterSet.set_id).where(BoosterSet.booster_id == booster.id)
        )).scalars().all() or [booster.set_id]
    generator = CardGeneratorService()
    for _ in range(5):
        pack = await generator.generate_pack(session, list(set_ids), cards_count=1, guaranteed_rare=False)
        if not pack:
            break
        data = pack[0]
        power = roll_power(data["drop_probability"], data["rarity_id"], data["quality_id"],
                           data["specialty_id"], data["jewelry_id"])
        if power is None:
            continue
        card = UserCard(
            user_id=0, character_id=data["character_id"], set_id=data["set_id"],
            rarity_id=data["rarity_id"], quality_id=data["quality_id"], specialty_id=data["specialty_id"],
            jewelry_id=data["jewelry_id"], drop_probability=data["drop_probability"], power=power,
        )
        return (await build_card_response(session, card)).model_dump(mode="json")
    raise HTTPException(503, "Aucune carte disponible pour ce mini-jeu.")


def _payout(game: HigherLowerGame, cfg: dict) -> int:
    return int(game.stake * cfg["higher_lower"]["multiplier"] ** game.step)


def _game_out(game: HigherLowerGame, cfg: dict, **extra) -> dict:
    hl = cfg["higher_lower"]
    return {
        "id": game.id, "status": game.status, "resource_id": game.resource_id, "stake": game.stake,
        "step": game.step, "max_steps": hl["max_steps"], "multiplier": hl["multiplier"],
        "current_card": game.current_card,
        "cashout_value": _payout(game, cfg) if game.status == "active" else game.payout,
        "next_value": int(game.stake * hl["multiplier"] ** (game.step + 1)),
        **extra,
    }


async def higher_lower_state(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    game = (await session.execute(
        select(HigherLowerGame).where(HigherLowerGame.user_id == user.id, HigherLowerGame.status == "active")
    )).scalars().first()
    hl = cfg["higher_lower"]
    return {
        "game": _game_out(game, cfg) if game else None,
        "min_stake": hl["min_stake"], "max_stake": hl["max_stake"],
        "multiplier": hl["multiplier"], "max_steps": hl["max_steps"],
    }


async def higher_lower_start(session: AsyncSession, user: User, resource_id: str, stake: int) -> dict:
    cfg = await activities_config.get_config(session)
    hl = cfg["higher_lower"]
    if resource_id not in STAKE_RESOURCES:
        raise HTTPException(400, "Mise possible en pièces ou en poussière uniquement.")
    if not hl["min_stake"] <= stake <= hl["max_stake"]:
        raise HTTPException(400, f"Mise entre {hl['min_stake']} et {hl['max_stake']}.")
    active = (await session.execute(
        select(HigherLowerGame.id).where(HigherLowerGame.user_id == user.id, HigherLowerGame.status == "active")
    )).first()
    if active:
        raise HTTPException(409, "Une partie est déjà en cours.")
    if await get_balance(session, user, resource_id) < stake:
        raise HTTPException(400, "Solde insuffisant pour cette mise.")

    await apply_delta(session, user, resource_id, -stake)
    game = HigherLowerGame(user_id=user.id, resource_id=resource_id, stake=stake,
                           current_card=await _random_card(session, cfg))
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return _game_out(game, cfg)


async def _active_game(session: AsyncSession, user: User, game_id: int) -> HigherLowerGame:
    game = (await session.execute(
        select(HigherLowerGame).where(HigherLowerGame.id == game_id).with_for_update()
    )).scalar_one_or_none()
    if not game or game.user_id != user.id:
        raise HTTPException(404, "Partie introuvable.")
    if game.status != "active":
        raise HTTPException(409, "Cette partie est terminée.")
    return game


async def _cash_out(session: AsyncSession, user: User, game: HigherLowerGame, cfg: dict) -> None:
    game.payout = _payout(game, cfg)
    game.status = "cashed"
    await apply_delta(session, user, game.resource_id, game.payout)


async def higher_lower_guess(session: AsyncSession, user: User, game_id: int, guess: str) -> dict:
    if guess not in ("higher", "lower"):
        raise HTTPException(400, "Réponse invalide.")
    cfg = await activities_config.get_config(session)
    game = await _active_game(session, user, game_id)
    previous = game.current_card
    card = await _random_card(session, cfg)
    before, after = previous["power"], card["power"]

    if after == before:
        outcome = "tie"  # égalité : on continue sans perdre
    elif (after > before) == (guess == "higher"):
        outcome = "win"
        game.step += 1
    else:
        outcome = "lose"
        game.status = "lost"
        game.payout = 0
    game.current_card = card
    if game.status == "active" and game.step >= cfg["higher_lower"]["max_steps"]:
        await _cash_out(session, user, game, cfg)
    session.add(game)
    await session.commit()
    return _game_out(game, cfg, outcome=outcome, previous_card=previous)


async def higher_lower_cashout(session: AsyncSession, user: User, game_id: int) -> dict:
    cfg = await activities_config.get_config(session)
    game = await _active_game(session, user, game_id)
    await _cash_out(session, user, game, cfg)
    session.add(game)
    await session.commit()
    return _game_out(game, cfg)


# ─────────────────────────────  ROUE DE LA FORTUNE  ─────────────────────────────

def _roll_wheel_day(row) -> None:
    today = datetime.utcnow().date()
    if row.wheel_day != today:
        row.wheel_day = today
        row.wheel_free_used = False
        row.wheel_extra_spins = 0


def _wheel_out(row, cfg: dict) -> dict:
    wheel = cfg["wheel"]
    return {
        "free_available": not row.wheel_free_used,
        "extra_spins_used": row.wheel_extra_spins,
        "extra_spins_per_day": wheel["extra_spins_per_day"],
        "extra_spin_cost": wheel["extra_spin_cost"],
        "segments": [{"label": s["label"], "kind": s["kind"]} for s in wheel["segments"]],
    }


async def wheel_state(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    row = await get_activity(session, user.id)
    _roll_wheel_day(row)
    session.add(row)
    await session.commit()
    return _wheel_out(row, cfg)


async def wheel_spin(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    wheel = cfg["wheel"]
    row = await get_activity(session, user.id)
    _roll_wheel_day(row)

    if not row.wheel_free_used:
        row.wheel_free_used = True
    elif row.wheel_extra_spins < wheel["extra_spins_per_day"]:
        cost = wheel["extra_spin_cost"]
        if user.coins < cost:
            raise HTTPException(400, f"Il faut {cost} pièces pour un tour supplémentaire.")
        await apply_delta(session, user, "coins", -cost)
        row.wheel_extra_spins += 1
    else:
        raise HTTPException(400, "Plus de tours disponibles aujourd'hui.")

    segments = wheel["segments"]
    index = random.choices(range(len(segments)), weights=[max(0, s.get("weight", 0)) for s in segments], k=1)[0]
    segment = segments[index]
    reward = {"kind": segment["kind"], "label": segment["label"], "amount": int(segment.get("amount", 1)),
              "resource_id": None, "booster_id": None, "booster_name": None}
    if segment["kind"] == "resource":
        reward["resource_id"] = segment["id"]
        await apply_delta(session, user, segment["id"], reward["amount"])
    elif segment["kind"] == "booster":
        booster = await session.get(Booster, segment.get("id") or cfg["reward_booster_id"])
        if booster:
            await booster_inventory.grant(session, user.id, booster.id, reward["amount"])
            reward["booster_id"], reward["booster_name"] = booster.id, booster.name
    elif segment["kind"] == "reroll":
        await reroll_inventory.grant_rules(
            session, user.id, None, "Reroll de la roue (rareté, garanti)", WHEEL_REROLL_RULES, reward["amount"],
        )

    session.add(row)
    await session.commit()
    return {"index": index, "reward": reward, "state": _wheel_out(row, cfg)}
