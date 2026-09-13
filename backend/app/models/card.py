"""
Modèle UserCard — Carte possédée par un joueur.
"""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class UserCard(SQLModel, table=True):
    __tablename__ = "user_cards"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
    )
    user_id: int = Field(foreign_key="users.id", index=True)

    # Références aux tables statiques
    character_id: str = Field(foreign_key="characters.id", index=True)
    set_id: str = Field(foreign_key="sets.id")
    rarity_id: str = Field(foreign_key="rarities.id", index=True)
    quality_id: str = Field(foreign_key="qualities.id")
    specialty_id: str = Field(foreign_key="specialties.id")
    jewelry_id: str = Field(default="none", foreign_key="jewelries.id")

    # Booster à l'origine de la carte (nullable : colonne ajoutée après coup,
    # les cartes plus anciennes n'en ont pas — cf. app/migrations.py)
    booster_id: Optional[str] = Field(default=None, max_length=30)

    # Probabilité calculée au moment de la génération
    drop_probability: float = Field(default=0.0)

    # Puissance tirée au hasard à l'obtention (cf. app/services/power.py) —
    # None si la carte n'a pas été obtenue par un tirage aléatoire.
    power: Optional[int] = Field(default=None)

    # URL de l'image rendue sur Cloudinary (ou chemin local en dev)
    rendered_url: Optional[str] = Field(default=None)

    # Timestamp
    obtained_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    # foreign_keys explicite : User.showcase_card_*_id pointe aussi vers cette
    # table (dans l'autre sens), donc SQLAlchemy ne peut plus déduire seul
    # quelle colonne joindre ici.
    user: Optional["User"] = Relationship(
        back_populates="cards",
        sa_relationship_kwargs={"foreign_keys": "UserCard.user_id"},
    )
