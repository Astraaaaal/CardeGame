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

    # Probabilité calculée au moment de la génération
    drop_probability: float = Field(default=0.0)

    # URL de l'image rendue sur Cloudinary (ou chemin local en dev)
    rendered_url: Optional[str] = Field(default=None)

    # Timestamp
    obtained_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    user: Optional["User"] = Relationship(back_populates="cards")
