"""
Mini-jeux : « plus ou moins » (deviner si la carte suivante est plus ou moins
puissante ; chaque bonne réponse multiplie le gain selon sa probabilité réelle,
avec une petite marge : le jeu est perdant à long terme) et roue de la fortune (un
tour gratuit par jour, les suivants en pièces). Mises uniquement en pièces ou
en poussière : jamais la monnaie premium, pour rester hors du cadre des jeux
d'argent. Tout le hasard est tiré côté serveur.
"""

import bisect
import random
import time
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.activity import HigherLowerGame
from app.models.booster import Booster, BoosterSet
from app.models.card import UserCard
from app.models.reference import Jewelry, Quality, Rarity, Specialty
from app.models.user import User
from app.services import activities_config, booster_inventory, reroll_inventory
from app.services.card_generator import CardGeneratorService
from app.services.card_view import build_card_response
from app.services.power import roll_drawn_power
from app.services.presence_bonus import get_activity
from app.services.wallet import apply_delta, get_balance
from app.services import unlocks
from app.services.wallet import require_balance

STAKE_RESOURCES = ("coins", "dust")
WHEEL_REROLL_RULES = {
    "reroll_rarity": True, "reroll_quality": False, "reroll_specialty": False,
    "reroll_jewelry": False, "reroll_power": False, "reroll_mode": "guaranteed_min",
}


# ─────────────────────────────  PLUS OU MOINS  ─────────────────────────────

async def _reward_set_ids(session: AsyncSession, cfg: dict) -> list[str]:
    booster = await session.get(Booster, cfg["reward_booster_id"])
    if not booster:
        return []
    return list((await session.execute(
        select(BoosterSet.set_id).where(BoosterSet.booster_id == booster.id)
    )).scalars().all() or [booster.set_id])


async def _random_card(session: AsyncSession, cfg: dict) -> dict:
    """Carte tirée au hasard dans les sets du booster de récompense (non attribuée)."""
    set_ids = await _reward_set_ids(session, cfg)
    generator = CardGeneratorService()
    for _ in range(5):
        pack = await generator.generate_pack(session, set_ids, cards_count=1, guaranteed_rare=False)
        if not pack:
            break
        data = pack[0]
        power = roll_drawn_power(data)
        if power is None:
            continue
        card = UserCard(
            user_id=0, character_id=data["character_id"], set_id=data["set_id"],
            rarity_id=data["rarity_id"], quality_id=data["quality_id"], specialty_id=data["specialty_id"],
            jewelry_id=data["jewelry_id"], drop_probability=data["drop_probability"], power=power,
        )
        return (await build_card_response(session, card)).model_dump(mode="json")
    raise HTTPException(503, "Aucune carte disponible pour ce mini-jeu.")


# Distribution des puissances des cartes tirées : échantillon simulé (même
# générateur, même tirage de puissance), mis en cache quelques minutes.
_SAMPLE_SIZE = 6000
_SAMPLE_TTL_S = 600
_sample_cache: dict = {}


async def _power_sample(session: AsyncSession, cfg: dict) -> list[int]:
    set_ids = await _reward_set_ids(session, cfg)
    key = tuple(sorted(set_ids))
    cached = _sample_cache.get(key)
    if cached and time.monotonic() - cached[0] < _SAMPLE_TTL_S:
        return cached[1]
    gen = CardGeneratorService()
    characters = await gen._get_characters_for_sets(session, list(set_ids))
    refs = [await gen._get_all(session, m) for m in (Rarity, Quality, Specialty, Jewelry)]
    powers = []
    if characters:
        for _ in range(_SAMPLE_SIZE):
            power = roll_drawn_power(gen._generate_single(characters, *refs))
            if power is not None:
                powers.append(power)
    powers.sort()
    _sample_cache[key] = (time.monotonic(), powers)
    return powers


async def _guess_multipliers(session: AsyncSession, cfg: dict, power: int) -> dict:
    """Gain d'une bonne réponse « plus » / « moins » depuis cette puissance
    (None si la réponse est impossible). L'égalité est neutre (×1)."""
    hl = cfg["higher_lower"]
    sample = await _power_sample(session, cfg)
    n = len(sample)
    if not n:
        return {"higher": None, "lower": None}
    below = bisect.bisect_left(sample, power) / n
    above = (n - bisect.bisect_right(sample, power)) / n
    tie = 1 - below - above

    def mult(p: float):
        if p <= 0:
            return None
        return round(min(hl["max_step_multiplier"], (1 - hl["house_edge"]) * (1 - tie) / p), 2)

    return {"higher": mult(above), "lower": mult(below)}


def _payout(game: HigherLowerGame) -> int:
    return int(game.stake * (game.total_multiplier or 1.0))


async def _game_out(session: AsyncSession, game: HigherLowerGame, cfg: dict, **extra) -> dict:
    hl = cfg["higher_lower"]
    active = game.status == "active"
    odds = await _guess_multipliers(session, cfg, game.current_card.get("power") or 0) if active else {}
    return {
        "id": game.id, "status": game.status, "resource_id": game.resource_id, "stake": game.stake,
        "step": game.step, "max_steps": hl["max_steps"], "min_cashout_step": hl["min_cashout_step"],
        "total_multiplier": round(game.total_multiplier or 1.0, 2),
        "current_card": game.current_card,
        "cashout_value": _payout(game) if active else game.payout,
        "can_cashout": active and game.step >= hl["min_cashout_step"],
        "odds": odds,
        **extra,
    }


async def higher_lower_state(session: AsyncSession, user: User) -> dict:
    cfg = await activities_config.get_config(session)
    game = (await session.execute(
        select(HigherLowerGame).where(HigherLowerGame.user_id == user.id, HigherLowerGame.status == "active")
    )).scalars().first()
    hl = cfg["higher_lower"]
    return {
        "game": await _game_out(session, game, cfg) if game else None,
        "min_stake": hl["min_stake"], "max_stake": unlocks.higher_lower_max_stake(cfg, await unlocks.level_of(session, user)),
        "max_steps": hl["max_steps"], "min_cashout_step": hl["min_cashout_step"],
    }


async def higher_lower_start(session: AsyncSession, user: User, resource_id: str, stake: int) -> dict:
    cfg = await activities_config.get_config(session)
    hl = cfg["higher_lower"]
    if resource_id not in STAKE_RESOURCES:
        raise HTTPException(400, "Mise possible en pièces ou en poussière uniquement.")
    max_stake = unlocks.higher_lower_max_stake(cfg, await unlocks.level_of(session, user))
    if not hl["min_stake"] <= stake <= max_stake:
        raise HTTPException(400, f"Mise entre {hl['min_stake']} et {max_stake} à ton niveau.")
    active = (await session.execute(
        select(HigherLowerGame.id).where(HigherLowerGame.user_id == user.id, HigherLowerGame.status == "active")
    )).first()
    if active:
        raise HTTPException(409, "Une partie est déjà en cours.")
    await require_balance(session, user, resource_id, stake)

    await apply_delta(session, user, resource_id, -stake)
    game = HigherLowerGame(user_id=user.id, resource_id=resource_id, stake=stake,
                           current_card=await _random_card(session, cfg))
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return await _game_out(session, game, cfg)


async def _active_game(session: AsyncSession, user: User, game_id: int) -> HigherLowerGame:
    game = (await session.execute(
        select(HigherLowerGame).where(HigherLowerGame.id == game_id).with_for_update()
    )).scalar_one_or_none()
    if not game or game.user_id != user.id:
        raise HTTPException(404, "Partie introuvable.")
    if game.status != "active":
        raise HTTPException(409, "Cette partie est terminée.")
    return game


async def _cash_out(session: AsyncSession, user: User, game: HigherLowerGame) -> None:
    game.payout = _payout(game)
    game.status = "cashed"
    await apply_delta(session, user, game.resource_id, game.payout)


async def higher_lower_guess(session: AsyncSession, user: User, game_id: int, guess: str) -> dict:
    if guess not in ("higher", "lower"):
        raise HTTPException(400, "Réponse invalide.")
    cfg = await activities_config.get_config(session)
    game = await _active_game(session, user, game_id)
    previous = game.current_card
    odds = await _guess_multipliers(session, cfg, previous.get("power") or 0)
    if odds.get(guess) is None:
        raise HTTPException(400, "Réponse impossible : aucune carte ne peut faire mieux.")
    card = await _random_card(session, cfg)
    before, after = previous["power"], card["power"]

    if after == before:
        outcome = "tie"  # égalité : neutre (×1), mais compte comme une manche
        game.step += 1
    elif (after > before) == (guess == "higher"):
        outcome = "win"
        game.step += 1
        game.total_multiplier = (game.total_multiplier or 1.0) * odds[guess]
    else:
        outcome = "lose"
        game.status = "lost"
        game.payout = 0
    game.current_card = card
    if game.status == "active" and game.step >= cfg["higher_lower"]["max_steps"]:
        await _cash_out(session, user, game)
    session.add(game)
    await session.commit()
    return await _game_out(session, game, cfg, outcome=outcome, previous_card=previous,
                           won_multiplier=odds[guess] if outcome == "win" else None)


async def higher_lower_cashout(session: AsyncSession, user: User, game_id: int) -> dict:
    cfg = await activities_config.get_config(session)
    game = await _active_game(session, user, game_id)
    if game.step < cfg["higher_lower"]["min_cashout_step"]:
        raise HTTPException(400, f"Encaissement possible à partir de {cfg['higher_lower']['min_cashout_step']} manches.")
    await _cash_out(session, user, game)
    session.add(game)
    await session.commit()
    return await _game_out(session, game, cfg)


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
        await require_balance(session, user, "coins", cost)
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
