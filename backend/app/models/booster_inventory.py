"""
Boosters possédés mais pas encore ouverts — récompenses (achievements,
niveaux, plus tard quêtes) qui donnent un booster n'ouvrent plus directement
les cartes : elles créditent ce solde, à ouvrir depuis la boutique (même
animation/flux que pour un booster acheté).
"""

from typing import Optional

from sqlmodel import SQLModel, Field


class UserBoosterInventory(SQLModel, table=True):
    __tablename__ = "user_booster_inventory"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    booster_id: str = Field(foreign_key="boosters.id", primary_key=True, max_length=30)
    quantity: int = Field(default=0)


class UserBonusBooster(SQLModel, table=True):
    """Booster acheté via une offre du shop à ressources et gardé pour plus
    tard : conserve le bonus de l'offre au moment de l'achat (rareté minimum
    garantie, chances boostées), même si l'offre change ou disparaît ensuite.
    Les exemplaires au bonus identique sont cumulés sur une même ligne."""
    __tablename__ = "user_bonus_boosters"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    booster_id: str = Field(foreign_key="boosters.id", max_length=30)
    force_min_rarity_id: Optional[str] = Field(default=None, max_length=20)
    rarity_weight_multiplier: Optional[float] = Field(default=None)
    label: str = Field(default="", max_length=100)
    quantity: int = Field(default=0)
