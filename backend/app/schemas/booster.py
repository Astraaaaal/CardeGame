"""
Schemas pour les boosters et l'ouverture de packs.
"""

from pydantic import BaseModel, Field
from typing import Literal
from app.schemas.card import CardResponse


class BoosterResponse(BaseModel):
    id: str
    name: str
    set_id: str  # premier set (compat) — cf. set_ids pour la liste complète
    set_ids: list[str] = []
    cards_count: int
    resource_id: str = "coins"
    resource_name: str = "Pièces"
    price: int
    guaranteed_rare: bool
    description: str = ""
    cover_image_url: str = ""


class PackOpenRequest(BaseModel):
    booster_id: str
    quantity: Literal[1, 5, 10] = 1


class PackOpenResponse(BaseModel):
    """Résultat de l'ouverture de packs."""
    packs: list[list[CardResponse]]
    total_cost: int
    remaining_coins: int  # compat : solde de pièces après achat (inchangé si payé en une autre ressource)
    resource_id: str = "coins"
    resource_name: str = "Pièces"
    new_balance: int = 0  # solde de la ressource utilisée pour payer, après achat
