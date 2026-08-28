"""
Modèles de référence — Tables statiques (anciennement JSON).
Sets, Rarities, Qualities, Specialties, Jewelries.
"""

from typing import Optional, List
from sqlmodel import SQLModel, Field, Column, ARRAY, Integer


class Set(SQLModel, table=True):
    __tablename__ = "sets"

    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=100)
    description: str = Field(default="")


class Rarity(SQLModel, table=True):
    __tablename__ = "rarities"

    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=50)
    weight: float = Field(default=1.0)
    color_r: int = Field(default=200)
    color_g: int = Field(default=200)
    color_b: int = Field(default=200)
    label_color_r: int = Field(default=200)
    label_color_g: int = Field(default=200)
    label_color_b: int = Field(default=200)

    @property
    def color(self) -> list[int]:
        return [self.color_r, self.color_g, self.color_b]

    @property
    def label_color(self) -> list[int]:
        return [self.label_color_r, self.label_color_g, self.label_color_b]


class Quality(SQLModel, table=True):
    __tablename__ = "qualities"

    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=50)
    weight: float = Field(default=1.0)
    filter_type: str = Field(default="none", max_length=30)
    description: str = Field(default="")


class Specialty(SQLModel, table=True):
    __tablename__ = "specialties"

    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=50)
    weight: float = Field(default=1.0)
    border_type: str = Field(default="default", max_length=30)
    effect: str = Field(default="none", max_length=30)
    description: str = Field(default="")


class Jewelry(SQLModel, table=True):
    __tablename__ = "jewelries"

    id: str = Field(primary_key=True, max_length=20)
    name: str = Field(max_length=50)
    weight: float = Field(default=1.0)
    color_r: int = Field(default=100)
    color_g: int = Field(default=100)
    color_b: int = Field(default=120)
    description: str = Field(default="")

    @property
    def color(self) -> list[int]:
        return [self.color_r, self.color_g, self.color_b]
