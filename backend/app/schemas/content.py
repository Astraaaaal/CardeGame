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
    set_ids: list[str] = Field(min_length=1)
    cards_count: int = Field(default=5, ge=1, le=20)
    resource_id: str = Field(default="coins", max_length=30)
    price: int = Field(default=100, ge=0, le=1_000_000)
    guaranteed_rare: bool = False
    description: str = ""
    active: bool = True
    visible_in_shop: bool = True
    cover_image_url: str = Field(default="", max_length=300)


class BoosterPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    set_ids: list[str] | None = Field(default=None, min_length=1)
    cards_count: int | None = Field(default=None, ge=1, le=20)
    resource_id: str | None = Field(default=None, max_length=30)
    price: int | None = Field(default=None, ge=0, le=1_000_000)
    guaranteed_rare: bool | None = None
    description: str | None = None
    active: bool | None = None
    visible_in_shop: bool | None = None
    cover_image_url: str | None = Field(default=None, max_length=300)


class BoosterOut(BaseModel):
    id: str
    name: str
    set_ids: list[str]
    cards_count: int
    resource_id: str = "coins"
    resource_name: str = "Pièces"
    price: int
    guaranteed_rare: bool
    description: str
    active: bool = True
    visible_in_shop: bool = True
    cover_image_url: str = ""


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


# ── Types de personnage ──

class TypeIn(BaseModel):
    id: str = Field(min_length=1, max_length=30, pattern=r"^[a-z0-9_.\-]+$")
    name: str = Field(min_length=1, max_length=30)
    color_r: int = Field(default=150, ge=0, le=255)
    color_g: int = Field(default=150, ge=0, le=255)
    color_b: int = Field(default=150, ge=0, le=255)


class TypePatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=30)
    color_r: int | None = Field(default=None, ge=0, le=255)
    color_g: int | None = Field(default=None, ge=0, le=255)
    color_b: int | None = Field(default=None, ge=0, le=255)


class TypeOut(BaseModel):
    id: str
    name: str
    color: list[int]
    in_use: int = 0
