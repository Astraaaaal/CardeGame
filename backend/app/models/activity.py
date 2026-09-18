"""
Activités hors combat : présence (bonus de chance + coffre d'absence),
expéditions de cartes, atelier à clics, mini-jeux (plus ou moins, roue).
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field


class UserActivity(SQLModel, table=True):
    """État des activités d'un joueur (une ligne par joueur, créée au besoin)."""
    __tablename__ = "user_activities"

    user_id: int = Field(foreign_key="users.id", primary_key=True)

    # Présence : début de la présence continue en cours et dernier signal reçu
    # (l'appli envoie un signal toutes les 30 s tant qu'elle est affichée).
    presence_since: Optional[datetime] = Field(default=None)
    presence_ping_at: Optional[datetime] = Field(default=None)
    # Coffre d'absence : secondes d'absence accumulées (plafonnées), à récupérer.
    chest_seconds: int = Field(default=0)

    # Atelier : taps de la jauge en cours, fragments de booster, jauges du jour.
    workshop_taps: int = Field(default=0)
    workshop_fragments: int = Field(default=0)
    workshop_gauges_today: int = Field(default=0)
    workshop_day: Optional[date] = Field(default=None)
    workshop_last_at: Optional[datetime] = Field(default=None)

    # Roue de la fortune : tours du jour.
    wheel_day: Optional[date] = Field(default=None)
    wheel_free_used: bool = Field(default=False)
    wheel_extra_spins: int = Field(default=0)


class Expedition(SQLModel, table=True):
    """Une équipe de 1 à 3 cartes partie en mission. Le butin est tiré au départ
    (et révélé au retour) : impossible de relancer le hasard en attendant."""
    __tablename__ = "expeditions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    slot: int = Field(default=0)
    duration_minutes: int = Field(default=15)
    card_ids: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False, default=list))
    total_power: int = Field(default=0)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ends_at: datetime = Field(default_factory=datetime.utcnow)
    # {"coins", "dust", "booster": bool, "rare_card": bool}
    loot: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    claimed_at: Optional[datetime] = Field(default=None)


class HigherLowerGame(SQLModel, table=True):
    """Partie de « plus ou moins » : la carte en cours est gardée côté serveur,
    la suivante n'est tirée qu'au moment de la réponse."""
    __tablename__ = "higher_lower_games"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    resource_id: str = Field(max_length=30)
    stake: int = Field(default=0)
    step: int = Field(default=0)
    current_card: dict = Field(default_factory=dict, sa_column=Column(JSON, nullable=False, default=dict))
    status: str = Field(default="active", max_length=10)  # active | cashed | lost
    payout: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
