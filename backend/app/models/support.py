"""
Signalements de bug envoyés par les joueurs (onglet "Support" du profil),
consultables depuis le panneau admin.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer
from sqlmodel import SQLModel, Field


class BugReport(SQLModel, table=True):
    __tablename__ = "bug_reports"

    id: Optional[int] = Field(default=None, primary_key=True)
    # ON DELETE SET NULL : si le compte est supprimé ensuite, le signalement
    # reste consultable par l'admin (username figé ci-dessous, pas de FK vivante).
    user_id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True),
    )
    username: str = Field(max_length=20)

    subject: str = Field(max_length=100)
    body: str = Field(max_length=2000)
    # Route front d'où vient le signalement (ex: "/collection"), pour contexte.
    page_context: Optional[str] = Field(default=None, max_length=200)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    resolved_at: Optional[datetime] = Field(default=None)
