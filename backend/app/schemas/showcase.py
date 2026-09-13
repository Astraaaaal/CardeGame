"""
Schemas — vitrine publique du joueur (avatar, cartes mises en avant, cartes à échanger).
"""

from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.card import CardResponse


class AvatarInfo(BaseModel):
    character_id: str
    character_name: str
    image_url: str


class TradeListingOut(BaseModel):
    slot: int
    card: CardResponse
    resource_id: str
    resource_name: str
    price: int
    mode: Literal["buy_now", "offer"]


class ShowcaseResponse(BaseModel):
    user_id: int
    username: str
    display_name: str
    avatar: AvatarInfo | None = None
    cards: list[CardResponse] = []  # 0 à 3, emplacements vides omis
    trade_listings: list[TradeListingOut] = []  # 0 à 3, emplacements vides omis


class UpdateShowcaseRequest(BaseModel):
    avatar_character_id: str | None = None
    card_slots: list[str | None] = Field(min_length=3, max_length=3)


class TradeListingSlotIn(BaseModel):
    user_card_id: str
    resource_id: str
    price: int = Field(ge=0)
    mode: Literal["buy_now", "offer"]


class UpdateTradeListingsRequest(BaseModel):
    slots: list[TradeListingSlotIn | None] = Field(min_length=3, max_length=3)
