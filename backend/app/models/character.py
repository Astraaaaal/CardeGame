"""
Modèles Character et CharacterSet — Personnages du jeu.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class Character(SQLModel, table=True):
    __tablename__ = "characters"

    id: str = Field(primary_key=True, max_length=30)
    name: str = Field(max_length=100)
    description: str = Field(default="")
    type: str = Field(max_length=30)
    gen: int = Field(default=1)
    image_url: str = Field(default="")


class CharacterSet(SQLModel, table=True):
    """Table de liaison personnage ↔ set avec poids."""
    __tablename__ = "character_sets"

    character_id: str = Field(
        foreign_key="characters.id",
        primary_key=True,
        max_length=30,
    )
    set_id: str = Field(
        foreign_key="sets.id",
        primary_key=True,
        max_length=20,
    )
    weight: float = Field(default=1.0)
