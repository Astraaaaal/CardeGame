"""
Guildes : groupe de joueurs avec rôles, défi hebdomadaire (3 objectifs dont la
difficulté monte de palier en palier), coffre alimenté par les dons (XP + points
à dépenser en bonus temporaires), mur de messages et classements.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field

ROLE_LEADER = "leader"
ROLE_OFFICER = "officer"
ROLE_MEMBER = "member"

POLICY_OPEN = "open"
POLICY_REQUEST = "request"
POLICY_INVITE = "invite"


class Guild(SQLModel, table=True):
    __tablename__ = "guilds"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=24, unique=True, index=True)
    tag: str = Field(max_length=4, unique=True, index=True)
    icon: str = Field(default="🛡️", max_length=8)
    color: str = Field(default="#6366f1", max_length=9)
    join_policy: str = Field(default=POLICY_REQUEST, max_length=10)
    welcome_message: str = Field(default="", max_length=300)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Niveau : XP gagnée par les dons et les objectifs réussis.
    xp: int = Field(default=0)
    # Points du coffre à dépenser en bonus, et total donné depuis la création.
    chest_points: int = Field(default=0)
    chest_total: int = Field(default=0)

    # Défi hebdomadaire : palier en cours et meilleur palier atteint.
    challenge_tier: int = Field(default=1)
    challenge_best_tier: int = Field(default=1)


class GuildMember(SQLModel, table=True):
    """Un joueur appartient à au plus une guilde (clé primaire = joueur)."""
    __tablename__ = "guild_members"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    guild_id: int = Field(foreign_key="guilds.id", index=True)
    role: str = Field(default=ROLE_MEMBER, max_length=10)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    donated_points: int = Field(default=0)


class GuildInvite(SQLModel, table=True):
    """Demande d'un joueur pour rejoindre (kind="request") ou invitation d'un
    officier à un joueur (kind="invite")."""
    __tablename__ = "guild_invites"

    id: Optional[int] = Field(default=None, primary_key=True)
    guild_id: int = Field(foreign_key="guilds.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    kind: str = Field(max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GuildMessage(SQLModel, table=True):
    """Mur de guilde. user_id NULL = message du système (arrivée, bonus acheté...)."""
    __tablename__ = "guild_messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    guild_id: int = Field(foreign_key="guilds.id", index=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    body: str = Field(max_length=300)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GuildWeek(SQLModel, table=True):
    """Défi d'une semaine : 3 objectifs {metric, target, progress, completed_at}."""
    __tablename__ = "guild_weeks"

    guild_id: int = Field(foreign_key="guilds.id", primary_key=True)
    week_key: str = Field(primary_key=True, max_length=10)
    tier: int = Field(default=1)
    objectives: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False, default=list))


class GuildContribution(SQLModel, table=True):
    """Contribution d'un membre à un objectif, et récupération de sa récompense."""
    __tablename__ = "guild_contributions"

    guild_id: int = Field(foreign_key="guilds.id", primary_key=True)
    week_key: str = Field(primary_key=True, max_length=10)
    metric: str = Field(primary_key=True, max_length=30)
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    count: int = Field(default=0)
    claimed_at: Optional[datetime] = Field(default=None)


class GuildBuff(SQLModel, table=True):
    """Bonus temporaire acheté avec les points du coffre, valable pour tous les membres."""
    __tablename__ = "guild_buffs"

    id: Optional[int] = Field(default=None, primary_key=True)
    guild_id: int = Field(foreign_key="guilds.id", index=True)
    kind: str = Field(max_length=20)
    expires_at: datetime
    bought_by: Optional[int] = Field(default=None, foreign_key="users.id")
