"""
Favoris : catégories créées par le joueur (nom + couleur, 10 au plus) dans
lesquelles il range des exemplaires précis de ses cartes pour les retrouver.
Un exemplaire peut appartenir à plusieurs catégories. Le verrou anti-recyclage
est à part (UserCard.locked).
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlmodel import Field, SQLModel

MAX_CATEGORIES = 10


class FavoriteCategory(SQLModel, table=True):
    __tablename__ = "favorite_categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=24)
    color: str = Field(max_length=9)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FavoriteCard(SQLModel, table=True):
    __tablename__ = "favorite_cards"

    category_id: int = Field(sa_column=Column(
        Integer, ForeignKey("favorite_categories.id", ondelete="CASCADE"), primary_key=True))
    user_card_id: str = Field(sa_column=Column(
        String, ForeignKey("user_cards.id", ondelete="CASCADE"), primary_key=True, index=True))
