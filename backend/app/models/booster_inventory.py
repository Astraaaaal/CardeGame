"""
Boosters possédés mais pas encore ouverts — récompenses (achievements,
niveaux, plus tard quêtes) qui donnent un booster n'ouvrent plus directement
les cartes : elles créditent ce solde, à ouvrir depuis la boutique (même
animation/flux que pour un booster acheté).
"""

from sqlmodel import SQLModel, Field


class UserBoosterInventory(SQLModel, table=True):
    __tablename__ = "user_booster_inventory"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    booster_id: str = Field(foreign_key="boosters.id", primary_key=True, max_length=30)
    quantity: int = Field(default=0)
