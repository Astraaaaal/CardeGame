"""
Modèle Booster — Packs achetables.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class Booster(SQLModel, table=True):
    __tablename__ = "boosters"

    id: str = Field(primary_key=True, max_length=30)
    name: str = Field(max_length=100)
    set_id: str = Field(foreign_key="sets.id", max_length=20)
    cards_count: int = Field(default=5)
    price: int = Field(default=100)
    guaranteed_rare: bool = Field(default=False)
    description: str = Field(default="")
