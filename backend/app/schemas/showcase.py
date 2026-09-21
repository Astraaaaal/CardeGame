"""
Schemas — vitrine publique du joueur (avatar, cartes mises en avant, cartes à échanger).
"""

from typing import Literal
from app.schemas.social import GuildTagOut
from pydantic import BaseModel, Field
from app.schemas.card import CardResponse
from app.schemas.premium import CosmeticOut


class AvatarInfo(BaseModel):
    character_id: str
    character_name: str
    image_url: str


class ShowcaseAchievement(BaseModel):
    id: str
    name: str
    description: str
    category: str


class TradeListingOut(BaseModel):
    slot: int
    card: CardResponse
    resource_id: str
    resource_name: str
    price: int
    mode: Literal["buy_now", "offer"]
    # Taxe (pièces) que paierait le joueur qui consulte la vitrine en l'achetant.
    tax: int = 0


class ShowcaseResponse(BaseModel):
    user_id: int
    username: str
    display_name: str
    avatar: AvatarInfo | None = None
    cards: list[CardResponse] = []  # 0 à 3, emplacements vides omis
    trade_listings: list[TradeListingOut] = []  # 0 à 3, emplacements vides omis
    # "self" | "friends" | "pending" | "none" — relation entre le visiteur et
    # ce joueur (cf. app/services/showcase_view.py), pour piloter le bouton
    # "Ajouter en ami" côté vitrine publique.
    friendship_status: str = "self"
    level: int = 1
    total_power: int = 0
    best_login_streak: int = 0
    current_global_rank: int | None = None
    best_global_rank: int | None = None
    achievements: list[ShowcaseAchievement] = []  # 0 à 3, emplacements vides omis
    # Emplacements bruts (3, None = vide) — pour que l'éditeur conserve l'ordre.
    achievement_slots: list[str | None] = [None, None, None]
    avatar_frame: CosmeticOut | None = None
    showcase_background: CosmeticOut | None = None
    guild: GuildTagOut | None = None


class UpdateShowcaseRequest(BaseModel):
    avatar_character_id: str | None = None
    card_slots: list[str | None] = Field(min_length=3, max_length=3)
    achievement_slots: list[str | None] = Field(default_factory=lambda: [None, None, None], min_length=3, max_length=3)


class TradeListingSlotIn(BaseModel):
    user_card_id: str
    resource_id: str
    price: int = Field(ge=0)
    mode: Literal["buy_now", "offer"]


class UpdateTradeListingsRequest(BaseModel):
    slots: list[TradeListingSlotIn | None] = Field(min_length=3, max_length=3)
