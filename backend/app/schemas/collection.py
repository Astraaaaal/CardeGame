"""
Schemas pour la collection.
"""

from pydantic import BaseModel
from typing import Optional, Literal
from app.schemas.card import CardGroupResponse


class CollectionFilters(BaseModel):
    sort_by: Literal[
        "rarity", "name", "quality", "specialty", "jewelry", "probability"
    ] = "rarity"
    set_id: Optional[str] = None
    rarity_id: Optional[str] = None
    specialty_id: Optional[str] = None
    jewelry_id: Optional[str] = None


class CollectionResponse(BaseModel):
    total_cards: int
    unique_cards: int
    groups: list[CardGroupResponse]
