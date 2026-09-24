"""
Niveaux — dérivés à la volée de la puissance totale (somme de UserCard.power),
comparés à la table de paliers éditable LevelTier. `User.claimed_level`
retient jusqu'où la récompense a déjà été récupérée (le niveau "affiché"
avance tout seul dès que la puissance suffit, indépendamment de la récupération).

Prestige : au-delà du dernier palier de la route, des niveaux sont générés sans
fin (réglages « prestige ») — chacun demande un pourcentage de puissance en plus
du précédent et rapporte la récompense du dernier palier, majorée, plus un bonus.
"""

import math
from types import SimpleNamespace

from sqlalchemy import case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.models.user import User
from app.models.card import UserCard
from app.models.booster import Booster
from app.models.economy import Resource
from app.models.level import LevelTier
from app.services.wallet import apply_delta
from app.services import activities_config, booster_inventory

# Niveaux de prestige générés (largement assez : +25 % par niveau dépasse vite
# toute puissance atteignable).
PRESTIGE_LEVELS = 100
# Route affichée : prestiges visibles au-delà du niveau atteint.
PRESTIGE_PREVIEW = 3


# Ce qu'une carte apporte AU NIVEAU, au maximum. Sa puissance reste entière
# partout ailleurs (fiche, classement, palmarès) : c'est seulement l'échelle
# des niveaux qui cesse de voir une carte chanceuse comme trois cents cartes.
# Sans ce plafond, un seul tirage heureux sautait dix niveaux d'un coup et la
# progression suivait la chance au lieu de suivre l'effort.
LEVEL_CONTRIBUTION_CAP = 150


async def get_total_power(session: AsyncSession, user_id: int) -> int:
    """Somme des contributions au niveau (puissances écrêtées), pas la
    puissance brute — cf. LEVEL_CONTRIBUTION_CAP."""
    contribution = case(
        (UserCard.power > LEVEL_CONTRIBUTION_CAP, LEVEL_CONTRIBUTION_CAP),
        else_=UserCard.power,
    )
    total = (await session.execute(
        select(func.sum(contribution)).where(UserCard.user_id == user_id, UserCard.power != None)  # noqa: E711
    )).scalar()
    return int(total or 0)


async def get_all_tiers(session: AsyncSession) -> list:
    """Paliers de la route (table LevelTier) suivis des niveaux de prestige générés."""
    rows = list((await session.execute(select(LevelTier).order_by(LevelTier.level))).scalars().all())
    if not rows or rows[-1].power_required <= 0:
        return rows
    cfg = (await activities_config.get_config(session))["prestige"]
    last = rows[-1]
    power = last.power_required
    for step in range(1, PRESTIGE_LEVELS + 1):
        power = math.ceil(power * (1 + float(cfg["power_growth"])))
        amount = round((last.reward_amount or 0) * (1 + float(cfg["reward_growth"]) * step))
        rows.append(SimpleNamespace(
            level=last.level + step, prestige=step, power_required=power,
            reward_resource_id=(last.reward_resource_id or "coins") if amount else None,
            reward_amount=amount or None, reward_booster_id=None,
            bonus_resource_id=cfg.get("bonus_resource_id"), bonus_amount=int(cfg.get("bonus_amount") or 0),
        ))
    return rows


def prestige_of(tier) -> int:
    return getattr(tier, "prestige", 0)


def current_level_for_power(tiers: list[LevelTier], total_power: int) -> int:
    """Le plus haut palier dont le seuil est atteint (tiers doit être trié par level croissant)."""
    level = tiers[0].level if tiers else 1
    for tier in tiers:
        if total_power >= tier.power_required:
            level = tier.level
        else:
            break
    return level


def _has_reward(tier) -> bool:
    return bool((tier.reward_resource_id and tier.reward_amount) or tier.reward_booster_id
                or (getattr(tier, "bonus_resource_id", None) and getattr(tier, "bonus_amount", 0)))


def _bonus(tier) -> dict:
    """Bonus des niveaux de prestige (en plus de la récompense habituelle)."""
    return {"bonus_resource_id": getattr(tier, "bonus_resource_id", None) or None,
            "bonus_amount": getattr(tier, "bonus_amount", 0) or None, "prestige": prestige_of(tier)}


async def get_status(session: AsyncSession, user: User) -> dict:
    tiers = await get_all_tiers(session)
    total_power = await get_total_power(session, user.id)
    current_level = current_level_for_power(tiers, total_power)
    next_tier = next((t for t in tiers if t.level > current_level), None)

    pending = [
        t for t in tiers
        if t.level > user.claimed_level and t.level <= current_level and _has_reward(t)
    ]
    booster_names = await _booster_names(session, pending)

    current_tier = next((t for t in tiers if t.level == current_level), None)
    return {
        "current_level": current_level,
        "prestige": prestige_of(current_tier) if current_tier else 0,
        "total_power": total_power,
        "claimed_level": user.claimed_level,
        # Seuil du niveau ATTEINT : sans lui, une barre de progression ne peut
        # que mesurer le chemin depuis zéro, et se retrouve presque pleine en
        # permanence au lieu de repartir à chaque palier.
        "current_level_power_required": current_tier.power_required if current_tier else 0,
        "next_level_power_required": next_tier.power_required if next_tier else None,
        "pending_rewards": [
            {
                "level": t.level, "reward_resource_id": t.reward_resource_id, "reward_amount": t.reward_amount,
                "reward_booster_id": t.reward_booster_id,
                "reward_booster_name": booster_names.get(t.reward_booster_id),
                **_bonus(t),
            }
            for t in pending
        ],
        "has_unclaimed": bool(pending),
    }


async def _booster_names(session: AsyncSession, tiers: list[LevelTier]) -> dict[str, str]:
    ids = {t.reward_booster_id for t in tiers if t.reward_booster_id}
    if not ids:
        return {}
    rows = (await session.execute(select(Booster).where(Booster.id.in_(ids)))).scalars().all()
    return {b.id: b.name for b in rows}


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
        if tier.reward_booster_id:
            await booster_inventory.grant(session, user.id, tier.reward_booster_id, 1)
        bonus = _bonus(tier)
        if bonus["bonus_resource_id"] and bonus["bonus_amount"]:
            await apply_delta(session, user, bonus["bonus_resource_id"], bonus["bonus_amount"])

    user.claimed_level = current_level
    session.add(user)
    await session.commit()
    return await get_status(session, user)


async def get_tiers_overview(session: AsyncSession, user: User) -> list[dict]:
    """Toute la table de paliers (pour la "route" style trophy road), avec
    l'état de chacun pour CE joueur (atteint / récupéré)."""
    tiers = await get_all_tiers(session)
    total_power = await get_total_power(session, user.id)
    current_level = current_level_for_power(tiers, total_power)
    # Prestiges : seulement ceux atteints et les quelques suivants.
    tiers = [t for t in tiers if not prestige_of(t) or t.level <= current_level + PRESTIGE_PREVIEW]

    resource_ids = {t.reward_resource_id for t in tiers if t.reward_resource_id}
    resource_ids |= {t.bonus_resource_id for t in tiers if getattr(t, "bonus_resource_id", None)}
    resources = {}
    if resource_ids:
        rows = (await session.execute(select(Resource).where(Resource.id.in_(resource_ids)))).scalars().all()
        resources = {r.id: r.name for r in rows}
    booster_names = await _booster_names(session, tiers)

    return [
        {
            "level": t.level, "power_required": t.power_required,
            "reward_resource_id": t.reward_resource_id,
            "reward_resource_name": resources.get(t.reward_resource_id),
            "reward_amount": t.reward_amount,
            "reward_booster_id": t.reward_booster_id,
            "reward_booster_name": booster_names.get(t.reward_booster_id),
            "reached": t.level <= current_level,
            "claimed": t.level <= user.claimed_level,
            **_bonus(t),
            "bonus_resource_name": resources.get(getattr(t, "bonus_resource_id", None)),
        }
        for t in tiers
    ]
