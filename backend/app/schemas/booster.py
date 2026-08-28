"""
Schemas pour les boosters et l'ouverture de packs.
"""

from pydantic import BaseModel, Field
from typing import Literal
from app.schemas.card import CardResponse


class BoosterResponse(BaseModel):
    id: str
    name: str
    set_id: str
    cards_count: int
    price: int
    guaranteed_rare: bool
    description: str = ""


class PackOpenRequest(BaseModel):
    booster_id: str
    quantity: Literal[1, 5, 10] = 1


class PackOpenResponse(BaseModel):
    """Résultat de l'ouverture de packs."""
    packs: list[list[CardResponse]]
    total_cost: int
    remaining_coins: int
