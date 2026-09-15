"""
Schemas pour le profil joueur.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.schemas.economy import ResourceBalance
from app.schemas.card import CardResponse


class PlayerResponse(BaseModel):
    id: int
    username: str
    display_name: str
    coins: int
    packs_opened: int
    total_cards: int
    login_streak: int
    created_at: datetime
    last_login: Optional[datetime] = None
    resources: list[ResourceBalance] = []
    allow_friend_requests: bool = True
    trade_request_policy: str = "friends"
    trade_request_popup_enabled: bool = True


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=20)


class DailyRewardResponse(BaseModel):
    reward: int
    streak: int
    is_new: bool
    total_coins: int


class PlayerStatsResponse(BaseModel):
    total_cards: int
    unique_cards: int
    packs_opened: int
    cards_recycled: int
    coins: int
    dust: int
    total_power: int
    average_power: float
    highest_power_card: Optional[CardResponse] = None
    luckiest_card: Optional[CardResponse] = None
    most_duplicated_card: Optional[CardResponse] = None
    most_duplicated_count: int
    friends_count: int
    trades_completed: int
    gifts_sent: int
    gifts_received: int
    current_level: int
    achievements_unlocked: int
    achievements_total: int
    login_streak: int
    favorite_type_name: Optional[str] = None
    favorite_type_count: int
    oldest_card: Optional[CardResponse] = None
