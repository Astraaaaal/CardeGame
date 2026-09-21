"""
Taxe sur les transferts entre joueurs (échanges, cadeaux, achats d'annonce).

Chacun paie, en pièces, sur ce qu'il REÇOIT. Le taux dépend du plus haut des
deux niveaux (plus haut niveau atteint) : il augmente avec le niveau, pour que
les meilleurs joueurs ne se renforcent pas entre eux sans frein. Valeur d'une
carte selon sa rareté globale (combinaison + puissance) : ~1 pièce pour une
commune faible, ~1 000 pour une légendaire moyenne, plafonnée.
"""

import math

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booster import Booster
from app.models.card import UserCard
from app.models.user import User
from app.services import activities_config, unlocks
from app.services.power import combined_rarity
from app.services.wallet import COINS_ID


async def rate_for(session: AsyncSession, a: User, b: User | None = None) -> float:
    cfg = await activities_config.get_config(session)
    tax = cfg["trade_tax"]
    level = await unlocks.level_of(session, a)
    if b is not None:
        level = max(level, await unlocks.level_of(session, b))
    start = unlocks.required_level(cfg, "trades")
    return round(min(tax["max_rate"], tax["base_rate"] + tax["per_level"] * max(0, level - start)), 4)


def card_value(cfg: dict, card: UserCard) -> float:
    tax = cfg["trade_tax"]
    rarity = combined_rarity(card.power, card.drop_probability, card.rarity_id, card.quality_id,
                             card.specialty_id, card.jewelry_id)
    if not rarity:
        rarity = round(1 / card.drop_probability) if card.drop_probability else tax["card_anchor"]
    return min(tax["card_cap"], (max(rarity, 1) / tax["card_anchor"]) ** tax["card_exponent"])


def _ceil(amount: float) -> int:
    return max(1, math.ceil(amount - 1e-9))


async def tax_for_items(session: AsyncSession, rate: float, items: list[dict]) -> int:
    """items : [{"type": "card", "card": UserCard} | {"type": "resource", "resource_id", "amount"}
    | {"type": "booster", "booster_id", "amount"} | {"type": "reroll", "amount"}]."""
    if not items:
        return 0
    cfg = await activities_config.get_config(session)
    tax = cfg["trade_tax"]
    total = 0
    for it in items:
        if it["type"] == "card":
            total += _ceil(card_value(cfg, it["card"]) * rate)
        elif it["type"] == "resource":
            # Pièces : pourcentage direct ; autres ressources : converties en valeur pièces.
            unit = 1 if it["resource_id"] == COINS_ID else tax["resource_values"].get(it["resource_id"], 1)
            total += _ceil(it["amount"] * unit * rate)
        elif it["type"] == "booster":
            booster = await session.get(Booster, it["booster_id"])
            unit = booster.price if booster and booster.resource_id == COINS_ID else tax["booster_value"]
            total += _ceil(unit * it["amount"] * rate)
        elif it["type"] == "reroll":
            total += _ceil(tax["reroll_value"] * it["amount"] * rate)
    return total
