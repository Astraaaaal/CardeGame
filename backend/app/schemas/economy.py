"""
Schemas — ressources, recyclage, shop.
"""

from datetime import date
from pydantic import BaseModel, Field
from app.schemas.card import CardResponse


class ResourceBalance(BaseModel):
    id: str
    name: str
    amount: int


class ResourceCatalogItem(BaseModel):
    """Ressource du catalogue, sans solde — pour peupler un sélecteur de monnaie côté joueur."""
    id: str
    name: str


class RecycleByIdsRequest(BaseModel):
    card_ids: list[str] = Field(min_length=1, max_length=999)


class RecycleByIdsResponse(BaseModel):
    resource_id: str
    resource_name: str
    gained: int
    new_balance: int
    recycled_count: int


class ShopOfferResponse(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    active: bool = True
    resource_id: str
    resource_name: str
    price: int
    purchase_limit_per_day: int | None = None
    purchases_today: int = 0  # renseigné uniquement dans la liste joueur
    is_daily_pool: bool = False
    featured_today: bool = False  # cette offre est LE booster du jour
    # aperçu, selon le kind
    booster_id: str | None = None
    force_min_rarity_id: str | None = None
    force_min_rarity_name: str | None = None
    rarity_weight_multiplier: float | None = None
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
    reroll_rarity: bool = False
    reroll_quality: bool = False
    reroll_specialty: bool = False
    reroll_jewelry: bool = False
    reroll_mode: str | None = None


class ShopBuyRequest(BaseModel):
    offer_id: str
    card_id: str | None = None  # requis pour kind="upgrade" et "reroll"


class ShopBuyResponse(BaseModel):
    message: str
    resource_id: str
    new_balance: int
    cards: list[CardResponse] = []  # booster (plusieurs) / specific_card / upgrade / reroll (une)


# ── Admin ──

class ShopOfferIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    kind: str = Field(pattern=r"^(booster|specific_card|reroll)$")
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    active: bool = True
    resource_id: str
    price: int = Field(ge=0)
    purchase_limit_per_day: int | None = Field(default=None, ge=1)
    is_daily_pool: bool = False

    booster_id: str | None = None
    force_min_rarity_id: str | None = None
    rarity_weight_multiplier: float | None = Field(default=None, gt=0, le=100)

    character_id: str | None = None
    rarity_id: str | None = None
    quality_id: str | None = None
    specialty_id: str | None = None
    jewelry_id: str | None = None

    reroll_rarity: bool = False
    reroll_quality: bool = False
    reroll_specialty: bool = False
    reroll_jewelry: bool = False
    reroll_mode: str | None = Field(default=None, pattern=r"^(random|guaranteed_min)$")


class ResourceIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=50)
    description: str = ""


class ResourcePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None


class DailyFeatureIn(BaseModel):
    offer_id: str
    feature_date: date | None = None  # défaut : aujourd'hui


class DailyFeatureOut(BaseModel):
    feature_date: date
    offer_id: str
    offer_name: str
