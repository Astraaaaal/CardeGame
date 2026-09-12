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


class CharacterType(SQLModel, table=True):
    """
    Types de personnage (Feu, Eau…), gérables depuis le panneau admin.
    `Character.type` reste une chaîne libre (le nom ici) pour compatibilité ;
    cette table est la source des couleurs et de la liste proposée à l'édition.
    """
    __tablename__ = "character_types"

    id: str = Field(primary_key=True, max_length=30)  # slug, ex: "feu"
    name: str = Field(max_length=30, unique=True)      # affiché, ex: "Feu"
    color_r: int = Field(default=150)
    color_g: int = Field(default=150)
    color_b: int = Field(default=150)

    @property
    def color(self) -> list[int]:
        return [self.color_r, self.color_g, self.color_b]
