"""
Schemas — ressources, recyclage, shop.
"""

from datetime import date
from typing import Literal

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
    card_ids: list[str] = Field(min_length=1, max_length=20_000)


class RecycleGainOut(BaseModel):
    resource_id: str
    name: str
    amount: int
    new_balance: int | None = None


class RecyclePreviewResponse(BaseModel):
    count: int
    gains: list[RecycleGainOut]


class RecycleByIdsResponse(BaseModel):
    # Poussière (compatibilité) ; toutes les ressources gagnées dans `gains`.
    resource_id: str
    resource_name: str
    gained: int
    new_balance: int
    recycled_count: int
    gains: list[RecycleGainOut] = []


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
    # Limite réglable : période (none | day | week | month | account) et nombre
    # autorisé, avec les achats déjà faits sur la période en cours.
    limit_period: str = "none"
    limit_count: int = 1
    purchases_in_period: int = 0
    grants: list[dict] = []  # kind = bundle
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
    reroll_power: bool = False
    reroll_mode: str | None = None
    cosmetic_id: str | None = None
    cosmetic_name: str | None = None
    card_power_mode: str = "rolled"
    card_power: int | None = None


class ShopBuyRequest(BaseModel):
    offer_id: str
    card_id: str | None = None  # requis pour kind="upgrade" et "reroll"
    # kind="booster" / "reroll" : garder dans l'inventaire (avec bonus / règles) au lieu d'utiliser tout de suite
    to_inventory: bool = False
    # ×N : boosters, cartes précises et rerolls mis en inventaire uniquement
    quantity: int = Field(default=1, ge=1, le=10)


class ShopBuyResponse(BaseModel):
    message: str
    resource_id: str
    new_balance: int
    cards: list[CardResponse] = []  # booster (1er pack) / specific_card (×N) / reroll (une)
    packs: list[list[CardResponse]] = []  # booster ouvert : un pack par exemplaire acheté
    previous_card: CardResponse | None = None  # reroll : la carte telle qu'elle était avant


class RerollTokenOut(BaseModel):
    id: int
    offer_id: str | None
    label: str
    quantity: int
    axes: list[str]
    reroll_power: bool
    reroll_mode: str | None


class RerollUseRequest(BaseModel):
    card_id: str


class RerollUseResponse(BaseModel):
    message: str
    previous_card: CardResponse
    card: CardResponse
    token: RerollTokenOut


# ── Admin ──

class ShopOfferIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    kind: str = Field(pattern=r"^(booster|specific_card|reroll|cosmetic|bundle)$")
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    active: bool = True
    resource_id: str
    price: int = Field(ge=0)
    purchase_limit_per_day: int | None = Field(default=None, ge=1)
    is_daily_pool: bool = False
    limit_period: Literal["none", "day", "week", "month", "account"] = "none"
    limit_count: int = Field(default=1, ge=1)
    grants: list[dict] = []

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
    reroll_power: bool = False
    reroll_mode: str | None = Field(default=None, pattern=r"^(random|guaranteed_min)$")

    cosmetic_id: str | None = None

    card_power_mode: str = Field(default="rolled", pattern=r"^(rolled|fixed)$")
    card_power: int | None = Field(default=None, ge=1)


class ShopOfferPatch(BaseModel):
    """Édition d'une offre existante — mêmes champs que ShopOfferIn, tous
    optionnels (id et kind exclus : on ne change pas la nature d'une offre,
    on la supprime et en recrée une autre si besoin)."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    active: bool | None = None
    resource_id: str | None = None
    price: int | None = Field(default=None, ge=0)
    purchase_limit_per_day: int | None = Field(default=None, ge=1)
    is_daily_pool: bool | None = None
    limit_period: Literal["none", "day", "week", "month", "account"] | None = None
    limit_count: int | None = Field(default=None, ge=1)
    grants: list[dict] | None = None

    booster_id: str | None = None
    force_min_rarity_id: str | None = None
    rarity_weight_multiplier: float | None = Field(default=None, gt=0, le=100)

    character_id: str | None = None
    rarity_id: str | None = None
    quality_id: str | None = None
    specialty_id: str | None = None
    jewelry_id: str | None = None

    reroll_rarity: bool | None = None
    reroll_quality: bool | None = None
    reroll_specialty: bool | None = None
    reroll_jewelry: bool | None = None
    reroll_power: bool | None = None
    reroll_mode: str | None = Field(default=None, pattern=r"^(random|guaranteed_min)$")

    cosmetic_id: str | None = None

    card_power_mode: str | None = Field(default=None, pattern=r"^(rolled|fixed)$")
    card_power: int | None = Field(default=None, ge=1)


class ResourceIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=50)
    description: str = ""


class ResourcePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = None
    starting_amount: int | None = Field(default=None, ge=0)


class DailyFeatureIn(BaseModel):
    offer_id: str
    feature_date: date | None = None  # défaut : aujourd'hui


class DailyFeatureOut(BaseModel):
    feature_date: date
    offer_id: str
    offer_name: str
