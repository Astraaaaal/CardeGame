"""
Reroll d'une carte possédée : re-tire un ou plusieurs axes (rareté, qualité,
spécialité, bijou) et/ou la puissance, selon des règles venant d'une offre du
shop (achat immédiat) ou d'un reroll gardé en inventaire.
"""

import random

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.card import UserCard
from app.models.character import Character, CharacterSet
from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.services.power import REFERENCE_SET_SIZE, power_range, roll_power
from app.services.card_generator import merge_full_art
from app.services.tier_order import rank

REROLL_MODELS = {
    "rarity": Rarity, "quality": Quality, "specialty": Specialty, "jewelry": Jewelry,
}
_FIELD_MAP = {"rarity": "rarity_id", "quality": "quality_id", "specialty": "specialty_id", "jewelry": "jewelry_id"}


def reroll_axes(rules) -> list[str]:
    """Axes relancés par des règles (ShopOffer ou UserRerollToken)."""
    return [
        a for a, on in [
            ("rarity", rules.reroll_rarity), ("quality", rules.reroll_quality),
            ("specialty", rules.reroll_specialty), ("jewelry", rules.reroll_jewelry),
        ] if on
    ]


async def _recompute_probability(session: AsyncSession, card: UserCard) -> tuple[float, float]:
    """Recalcule la probabilité affichée et celle qui fixe la plage de puissance.
    Identiques depuis que les deux se lisent sur le set de référence, mais
    gardées séparées : les cartes d'avant ce changement ont encore deux valeurs
    différentes en base."""
    links = (await session.execute(
        select(CharacterSet).where(CharacterSet.set_id == card.set_id)
    )).scalars().all()
    char_total = sum(l.weight for l in links) or 0
    mine = next((l for l in links if l.character_id == card.character_id), None)
    # Même normalisation que le générateur : le poids RELATIF du personnage dans
    # son set est conservé, la TAILLE du set est effacée (cf.
    # card_generator._generate_single et REFERENCE_SET_SIZE).
    char_prob = ((mine.weight / char_total) * len(links) / REFERENCE_SET_SIZE) if (mine and char_total) else 0.0

    async def frac(model, id_):
        rows = (await session.execute(select(model))).scalars().all()
        total = sum(r.weight for r in rows)
        item = next((r for r in rows if r.id == id_), None)
        return (item.weight / total) if (item and total) else 0.0

    specialty = await frac(Specialty, card.specialty_id)
    character = await session.get(Character, card.character_id)
    if card.specialty_id == "normal" and not (character and character.full_art):
        specialty += await frac(Specialty, "full_art")  # sans full art, sa part revient à « normale »
    axes = (
        await frac(Rarity, card.rarity_id)
        * await frac(Quality, card.quality_id)
        * specialty
        * await frac(Jewelry, card.jewelry_id)
    )
    # Pas d'arrondi : les combinaisons ultra-rares descendent sous 1e-12 et
    # tomberaient à 0 (plus aucune puissance possible).
    combinee = char_prob * axes
    return combinee, combinee


async def apply_reroll(session: AsyncSession, card: UserCard, rules) -> None:
    """Relance la carte selon les règles. Ne commit pas."""
    axes = reroll_axes(rules)
    if not axes and not rules.reroll_power:
        raise HTTPException(status_code=500, detail="Reroll mal configuré (aucun axe).")

    for axis in axes:
        items = (await session.execute(select(REROLL_MODELS[axis]))).scalars().all()
        current_rank = rank(axis, getattr(card, _FIELD_MAP[axis]))
        # Bonus de la machine : chances multipliées pour les paliers meilleurs que l'actuel.
        boost = getattr(rules, "reroll_boost", None)
        weights = [i.weight * (boost if boost and rank(axis, i.id) > current_rank else 1) for i in items]
        if axis == "specialty":
            char = await session.get(Character, card.character_id)
            if not (char and char.full_art):
                weights = merge_full_art(items, weights)  # pas de full art pour ce personnage
        picked = random.choices(items, weights=weights, k=1)[0]
        # « Garanti égal ou mieux » : tirage normal ; s'il est moins bien, la carte
        # garde son palier actuel (les paliers supérieurs restent à leur chance de base).
        if rules.reroll_mode == "guaranteed_min" and rank(axis, picked.id) < current_rank:
            continue
        setattr(card, _FIELD_MAP[axis], picked.id)

    card.drop_probability, card.power_probability = await _recompute_probability(session, card)
    max_power = power_range(
        card.power_probability, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id,
    )
    if rules.reroll_power or card.power is None:
        # Nouveau tirage dans la plage de la combinaison (éventuellement nouvelle).
        card.power = roll_power(
            card.power_probability, card.rarity_id, card.quality_id,
            card.specialty_id, card.jewelry_id,
        )
    elif max_power is not None and card.power > max_power:
        # Seuls les autres axes sont relancés : la puissance est conservée, mais
        # redescend au maximum possible si la nouvelle combinaison est plus commune.
        card.power = max_power
    session.add(card)


async def assign_bought_card_power(session: AsyncSession, card: UserCard, offer=None) -> None:
    """Carte obtenue sans tirage (achat d'une carte précise) : vraie probabilité
    de la combinaison, puis puissance fixée par l'offre (plafonnée au maximum
    possible) ou tirée dans la plage. Ne commit pas."""
    card.drop_probability, card.power_probability = await _recompute_probability(session, card)
    max_power = power_range(
        card.power_probability, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id,
    )
    if offer is not None and offer.card_power_mode == "fixed" and offer.card_power:
        card.power = min(offer.card_power, max_power) if max_power else offer.card_power
    else:
        card.power = roll_power(
            card.power_probability, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id,
        )


async def backfill_missing_powers(session: AsyncSession) -> int:
    """Cartes déjà achetées sans puissance : leur en tire une. Ne commit pas."""
    cards = (await session.execute(select(UserCard).where(UserCard.power.is_(None)))).scalars().all()
    for card in cards:
        await assign_bought_card_power(session, card)
        session.add(card)
    return len(cards)
