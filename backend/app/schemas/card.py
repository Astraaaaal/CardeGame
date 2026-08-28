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
    rendered_url: Optional[str] = None
    obtained_at: Optional[datetime] = None


class CardGroupResponse(BaseModel):
    """Carte groupée avec compteur (pour la collection)."""
    card: CardResponse
    quantity: int = 1
