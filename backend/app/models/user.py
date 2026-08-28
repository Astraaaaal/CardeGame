"""
Modèle User — Joueur avec ses stats et credentials.
"""

from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.card import UserCard
    from app.models.token import RefreshToken


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=20, unique=True, index=True)
    display_name: str = Field(max_length=20)
    password_hash: str = Field(max_length=256)

    # Économie
    coins: int = Field(default=500)

    # Stats
    packs_opened: int = Field(default=0)
    total_cards: int = Field(default=0)

    # Streak
    login_streak: int = Field(default=0)
    last_daily_claim: Optional[date] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)

    # Relations
    cards: List["UserCard"] = Relationship(back_populates="user")
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")
