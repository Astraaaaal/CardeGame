"""
Schemas — ressources, recyclage, shop.
"""

from pydantic import BaseModel, Field
from app.schemas.card import CardResponse


class ResourceBalance(BaseModel):
    id: str
    name: str
    amount: int


class RecycleRequest(BaseModel):
    character_id: str
    rarity_id: str
    quality_id: str
    specialty_id: str
    jewelry_id: str
    count: int = Field(ge=1, le=999)


class RecycleResponse(BaseModel):
    resource_id: str
    resource_name: str
    gained: int
    new_balance: int
    remaining_quantity: int


class ShopOfferResponse(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    active: bool = True
    resource_id: str
    resource_name: str
    price: int
    # aperçu, selon le kind
    booster_id: str | None = None
    character_id: str | None = None
    character_name: str | None = None
    rarity_id: str | None = None
    rarity_name: str | None = None
    quality_id: str | None = None
    quality_name: str | None = None
    specialty_id: str | None = None
    specialty_name: str | None = None
    jewelry_id: str | None = None
    jewelry_name: str | None = None
    target_quality_id: str | None = None
    target_quality_name: str | None = None
    target_specialty_id: str | None = None
    target_specialty_name: str | None = None


class ShopBuyRequest(BaseModel):
    offer_id: str
    card_id: str | None = None  # requis pour kind="upgrade"


class ShopBuyResponse(BaseModel):
    message: str
    resource_id: str
    new_balance: int
    cards: list[CardResponse] = []  # booster (plusieurs) / specific_card / upgrade (une)


# ── Admin ──

class ShopOfferIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    kind: str = Field(pattern=r"^(booster|specific_card|upgrade)$")
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    active: bool = True
    resource_id: str
    price: int = Field(ge=0)
    booster_id: str | None = None
    character_id: str | None = None
    rarity_id: str | None = None
    quality_id: str | None = None
    specialty_id: str | None = None
    jewelry_id: str | None = None
    target_quality_id: str | None = None
    target_specialty_id: str | None = None


class ResourceIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=50)
    description: str = ""
