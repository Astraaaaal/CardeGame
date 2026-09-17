"""
Schemas — boutique premium (cosmétiques, produits en euros, commandes).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CosmeticKind = Literal["avatar_frame", "showcase_background"]
CosmeticAnimation = Literal["none", "shine", "pulse", "rainbow"]
HexColor = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class CosmeticOut(BaseModel):
    id: str
    kind: CosmeticKind
    name: str
    description: str = ""
    color_from: str
    color_to: str
    animation: CosmeticAnimation = "none"
    image_url: str = ""
    active: bool = True


class CosmeticIn(BaseModel):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_.\-]+$")
    kind: CosmeticKind
    name: str = Field(min_length=1, max_length=60)
    description: str = ""
    color_from: str = HexColor
    color_to: str = HexColor
    animation: CosmeticAnimation = "none"
    image_url: str = Field(default="", max_length=300)
    active: bool = True


class CosmeticPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    description: str | None = None
    color_from: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    color_to: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    animation: CosmeticAnimation | None = None
    image_url: str | None = Field(default=None, max_length=300)
    active: bool | None = None


class GrantIn(BaseModel):
    kind: Literal["resource", "booster", "cosmetic"]
    id: str = Field(min_length=1, max_length=40)
    amount: int = Field(default=1, ge=1)


class GrantOut(GrantIn):
    name: str


class PremiumProductOut(BaseModel):
    id: str
    name: str
    description: str = ""
    price_cents: int
    currency: str
    grants: list[GrantOut] = []
    once_per_account: bool = False
    already_purchased: bool = False  # pour un produit « une fois par compte »
    active: bool = True
    sort_order: int = 0


class PremiumProductIn(BaseModel):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=80)
    description: str = ""
    price_cents: int = Field(ge=50)  # minimum Stripe : 0,50 €
    currency: Literal["eur"] = "eur"
    grants: list[GrantIn] = Field(min_length=1)
    once_per_account: bool = False
    active: bool = True
    sort_order: int = 0


class PremiumProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    price_cents: int | None = Field(default=None, ge=50)
    grants: list[GrantIn] | None = Field(default=None, min_length=1)
    once_per_account: bool | None = None
    active: bool | None = None
    sort_order: int | None = None


class PremiumStatusOut(BaseModel):
    access: bool
    shards: int = 0
    payments_available: bool = False  # Stripe configuré côté serveur


class CheckoutRequest(BaseModel):
    product_id: str


class CheckoutResponse(BaseModel):
    url: str


class MyCosmeticsOut(BaseModel):
    owned: list[CosmeticOut] = []
    equipped_avatar_frame_id: str | None = None
    equipped_showcase_background_id: str | None = None


class EquipCosmeticsRequest(BaseModel):
    avatar_frame_id: str | None = None
    showcase_background_id: str | None = None


class PremiumOrderOut(BaseModel):
    id: int
    username: str | None
    product_name: str
    amount_cents: int
    currency: str
    status: str
    created_at: datetime
    paid_at: datetime | None = None


class PremiumConfigOut(BaseModel):
    premium_shop_enabled: bool
    premium_testers: str
    stripe_configured: bool
    email_configured: bool


class PremiumConfigPatch(BaseModel):
    premium_shop_enabled: bool | None = None
    premium_testers: str | None = Field(default=None, max_length=2000)
