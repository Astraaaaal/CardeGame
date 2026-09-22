"""
Défi du mois : points (puissance des cartes obtenues pendant le mois) par
joueur et par guilde, et résultat de chaque mois une fois clôturé.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column
from sqlmodel import Field, SQLModel


class MonthlyScore(SQLModel, table=True):
    __tablename__ = "monthly_scores"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    month_key: str = Field(primary_key=True, max_length=7)  # "2026-09"
    points: int = Field(default=0, sa_column=Column(BigInteger, nullable=False, default=0))


class GuildMonthlyScore(SQLModel, table=True):
    """Points gagnés par les membres pendant qu'ils étaient dans la guilde (pas de
    clé étrangère : une guilde dissoute garde sa ligne, simplement ignorée)."""
    __tablename__ = "guild_monthly_scores"

    guild_id: int = Field(primary_key=True)
    month_key: str = Field(primary_key=True, max_length=7)
    points: int = Field(default=0, sa_column=Column(BigInteger, nullable=False, default=0))


class MonthlyResult(SQLModel, table=True):
    """Mois clôturé : récompenses envoyées, champions retenus (badge le mois suivant)."""
    __tablename__ = "monthly_results"

    month_key: str = Field(primary_key=True, max_length=7)
    finalized_at: datetime = Field(default_factory=datetime.utcnow)
    champion_user_id: Optional[int] = Field(default=None)
    champion_guild_id: Optional[int] = Field(default=None)
