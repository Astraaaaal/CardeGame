"""
Schemas pour les cartes.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CardResponse(BaseModel):
    id: str
    character_id: str
    character_name: str = ""
    character_type: str = ""
    character_description: str = ""
    gen: int = 1
    image_url: str = ""
    set_id: str
    set_name: str = ""
    rarity_id: str
    rarity_name: str = ""
    rarity_color: list[int] = [200, 200, 200]
    quality_id: str
    quality_name: str = ""
    specialty_id: str
    specialty_name: str = ""
    jewelry_id: str = "none"
    jewelry_name: str = "Commune"
    jewelry_color: list[int] = [100, 100, 120]
    drop_probability: float = 0.0
    power: Optional[int] = None
    combined_rarity: Optional[int] = None
    rendered_url: Optional[str] = None
    obtained_at: Optional[datetime] = None
    booster_id: Optional[str] = None
    booster_name: Optional[str] = None
    booster_cover_url: Optional[str] = None


class CardGroupResponse(BaseModel):
    """Carte groupée avec compteur (pour la collection)."""
    card: CardResponse
    quantity: int = 1


class CardCopyOut(BaseModel):
    """Un exemplaire précis (id + puissance) d'une combinaison possédée —
    sert à choisir LEQUEL apporter dans une session d'échange, un cadeau,
    ou recycler précisément."""
    id: str
    power: Optional[int] = None


class CardCopiesResponse(BaseModel):
    copies: list[CardCopyOut] = []
