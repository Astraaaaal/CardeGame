"""
Schemas pour l'édition de contenu (panneau admin) : sets, boosters, personnages.
"""

from pydantic import BaseModel, Field


# ── Sets ──

class SetIn(BaseModel):
    id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=100)
    description: str = ""


class SetPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class SetOut(BaseModel):
    id: str
    name: str
    description: str
    booster_count: int = 0
    character_count: int = 0


# ── Boosters ──

class BoosterIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=100)
    set_id: str = Field(min_length=1, max_length=20)
    cards_count: int = Field(default=5, ge=1, le=20)
    price: int = Field(default=100, ge=0, le=1_000_000)
    guaranteed_rare: bool = False
    description: str = ""


class BoosterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    set_id: str | None = None
    cards_count: int | None = Field(default=None, ge=1, le=20)
    price: int | None = Field(default=None, ge=0, le=1_000_000)
    guaranteed_rare: bool | None = None
    description: str | None = None


class BoosterOut(BaseModel):
    id: str
    name: str
    set_id: str
    cards_count: int
    price: int
    guaranteed_rare: bool
    description: str


# ── Personnages ──

class CharacterSetLink(BaseModel):
    set_id: str
    weight: float = Field(default=1.0, gt=0, le=10_000)


class CharacterIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    type: str = Field(default="Normal", max_length=30)
    gen: int = Field(default=1, ge=1, le=99)
    image_url: str = Field(default="", max_length=300)
    sets: list[CharacterSetLink] = []


class CharacterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    type: str | None = Field(default=None, max_length=30)
    gen: int | None = Field(default=None, ge=1, le=99)
    image_url: str | None = Field(default=None, max_length=300)
    sets: list[CharacterSetLink] | None = None  # si fourni, remplace tous les liens


class CharacterOut(BaseModel):
    id: str
    name: str
    description: str
    type: str
    gen: int
    image_url: str
    sets: list[CharacterSetLink] = []
