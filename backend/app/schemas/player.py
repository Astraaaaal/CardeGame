"""
Schemas pour le profil joueur.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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


class DailyRewardResponse(BaseModel):
    reward: int
    streak: int
    is_new: bool
    total_coins: int
