"""
Ce que rapporte le recyclage d'une carte (cf. réglages « recycling »).

Toute carte donne de la poussière (plage selon sa rareté) ; chaque palier
atteint sur une caractéristique ajoute sa ressource (fragment, minerai,
matière de spécialité, poussière de qualité). Dans chaque plage [min, max],
la puissance de la carte rapportée à SON maximum fixe une valeur cible (un
excellent tirage vise le maximum), puis la quantité est tirée au hasard dans
une fourchette autour de cette cible (± « spread », sans sortir de la plage).
"""

import math
import random
from collections import Counter

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.booster import Booster
from app.models.economy import ShopOffer
from app.services.power import power_range
from app.services.resource_catalog import DUST_ID


def power_ratio(card) -> float:
    """Place de la puissance dans la plage de la carte : 0 (minimum) → 1 (maximum)."""
    top = power_range(card.drop_probability, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id)
    if not card.power or not top or top <= 1:
        return 0.0
    return min(1.0, max(0.0, (card.power - 1) / (top - 1)))


def _fork(bounds, ratio: float, spread: float) -> tuple[int, int]:
    """Fourchette [bas, haut] autour de la cible donnée par la puissance, dans la plage."""
    low, high = int(bounds[0]), int(bounds[1])
    target = low + (high - low) * ratio
    bottom = min(high, max(low, math.floor(target * (1 - spread))))
    top = max(bottom, min(high, math.ceil(target * (1 + spread))))
    return bottom, top


def card_forks(card, cfg: dict) -> dict[str, tuple[int, int]]:
    """Fourchette de chaque ressource que peut rapporter la carte : {id: (bas, haut)}."""
    rules = cfg["recycling"]
    ratio = power_ratio(card)
    spread = float(rules.get("spread", 0))
    forks: dict[str, tuple[int, int]] = {}

    def add(resource_id, bounds):
        bottom, top = _fork(bounds, ratio, spread)
        prev = forks.get(resource_id, (0, 0))
        forks[resource_id] = (prev[0] + bottom, prev[1] + top)

    dust_bounds = rules["dust_by_rarity"].get(card.rarity_id)
    if dust_bounds:
        add(DUST_ID, dust_bounds)
    for axis, tier in (("rarity", card.rarity_id), ("jewelry", card.jewelry_id),
                       ("specialty", card.specialty_id), ("quality", card.quality_id)):
        resource_id = rules[axis].get(tier)
        bounds = rules["ranges"].get(resource_id) if resource_id else None
        if bounds:
            add(resource_id, bounds)
    return forks


def card_yield(card, cfg: dict) -> Counter:
    """Ressources rapportées par une carte, tirées dans leur fourchette : {id: quantité}."""
    return Counter({res_id: random.randint(bottom, top) for res_id, (bottom, top) in card_forks(card, cfg).items()})


def total_forks(cards, cfg: dict) -> dict[str, tuple[int, int]]:
    """Fourchette totale de plusieurs cartes (aperçu avant recyclage)."""
    total: dict[str, tuple[int, int]] = {}
    for card in cards:
        for res_id, (bottom, top) in card_forks(card, cfg).items():
            prev = total.get(res_id, (0, 0))
            total[res_id] = (prev[0] + bottom, prev[1] + top)
    return total


# Offres de départ payées en fragments : un booster à rareté garantie.
_STARTER_OFFERS = [
    ("frag_booster_rare", "Booster rare garanti", "frag_rare", 5, "rare"),
    ("frag_booster_epic", "Booster épique garanti", "frag_epic", 8, "epic"),
    ("frag_booster_legendary", "Booster légendaire garanti", "frag_legendary", 15, "legendary"),
]


async def seed_starter_offers(session: AsyncSession, booster_id: str) -> None:
    """Crée les offres de départ si elles n'existent pas (modifiables ensuite dans l'admin). Ne commit pas."""
    if not await session.get(Booster, booster_id):
        booster_id = (await session.execute(
            select(Booster.id).where(Booster.active == True).order_by(Booster.id)  # noqa: E712
        )).scalars().first()
        if not booster_id:
            return
    for offer_id, name, resource_id, price, rarity in _STARTER_OFFERS:
        if await session.get(ShopOffer, offer_id):
            continue
        session.add(ShopOffer(
            id=offer_id, kind="booster", name=name, resource_id=resource_id, price=price,
            description="Un booster dont une carte est au moins de cette rareté.",
            booster_id=booster_id, force_min_rarity_id=rarity,
        ))
