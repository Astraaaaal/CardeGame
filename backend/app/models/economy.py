"""
Modèles économie secondaire — ressources (recyclage), shop.
"""

from typing import Optional
from sqlmodel import SQLModel, Field


class Resource(SQLModel, table=True):
    """Une ressource (monnaie secondaire) obtenue par recyclage, dépensée au shop."""
    __tablename__ = "resources"

    id: str = Field(primary_key=True, max_length=30)  # slug, ex: "dust"
    name: str = Field(max_length=50)                   # ex: "Poussière"
    description: str = Field(default="")


class UserResource(SQLModel, table=True):
    """Solde d'un joueur pour une ressource donnée."""
    __tablename__ = "user_resources"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    resource_id: str = Field(foreign_key="resources.id", primary_key=True, max_length=30)
    amount: int = Field(default=0)


class ShopOffer(SQLModel, table=True):
    """
    Offre du shop à ressources. Une table unique, plusieurs `kind` :
    - "booster"          : ouvre 1 pack du booster `booster_id`
    - "specific_card"    : donne directement une carte avec la combinaison fixée
    - "upgrade"          : améliore une carte déjà possédée (qualité et/ou spécialité)
    Les colonnes non pertinentes pour un `kind` donné restent NULL.
    """
    __tablename__ = "shop_offers"

    id: str = Field(primary_key=True, max_length=30)
    kind: str = Field(max_length=20)  # booster | specific_card | upgrade
    name: str = Field(max_length=100)
    description: str = Field(default="")
    active: bool = Field(default=True)

    resource_id: str = Field(foreign_key="resources.id", max_length=30)
    price: int = Field(default=0)

    # kind = booster
    booster_id: Optional[str] = Field(default=None, foreign_key="boosters.id", max_length=30)

    # kind = specific_card
    character_id: Optional[str] = Field(default=None, foreign_key="characters.id", max_length=30)
    rarity_id: Optional[str] = Field(default=None, foreign_key="rarities.id", max_length=20)
    quality_id: Optional[str] = Field(default=None, foreign_key="qualities.id", max_length=20)
    specialty_id: Optional[str] = Field(default=None, foreign_key="specialties.id", max_length=20)
    jewelry_id: Optional[str] = Field(default=None, foreign_key="jewelries.id", max_length=20)

    # kind = upgrade (le joueur choisit QUELLE carte il possède au moment de l'achat ;
    # ces deux champs indiquent le palier cible s'ils sont fournis)
    target_quality_id: Optional[str] = Field(default=None, foreign_key="qualities.id", max_length=20)
    target_specialty_id: Optional[str] = Field(default=None, foreign_key="specialties.id", max_length=20)
