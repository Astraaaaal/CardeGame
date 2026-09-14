"""
Schemas pour la collection.
"""

from pydantic import BaseModel
from typing import Optional, Literal
from app.schemas.card import CardGroupResponse

TierOp = Literal["eq", "gte", "lte"]


class CollectionFilters(BaseModel):
    sort_by: Literal[
        "rarity", "name", "quality", "specialty", "jewelry", "probability", "obtained_at", "power", "luck"
    ] = "rarity"
    set_id: Optional[str] = None
    rarity_id: Optional[str] = None
    rarity_op: TierOp = "eq"
    quality_id: Optional[str] = None
    quality_op: TierOp = "eq"
    specialty_id: Optional[str] = None
    specialty_op: TierOp = "eq"
    jewelry_id: Optional[str] = None
    jewelry_op: TierOp = "eq"


class CollectionResponse(BaseModel):
    total_cards: int
    unique_cards: int
    groups: list[CardGroupResponse]


class ProbabilityItem(BaseModel):
    id: str
    name: str
    weight: float
    percentage: float


class ProbabilityTableResponse(BaseModel):
    rarities: list[ProbabilityItem]
    qualities: list[ProbabilityItem]
    specialties: list[ProbabilityItem]
    jewelries: list[ProbabilityItem]
