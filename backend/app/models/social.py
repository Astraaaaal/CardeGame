"""
Modèles social — demandes d'ami et demandes d'échange (placeholder).
"""

from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class FriendRequest(SQLModel, table=True):
    """
    Une ligne = une relation entre deux joueurs.
    - status = "pending"  : demande envoyée, en attente de réponse de `addressee_id`
    - status = "accepted" : la ligne EST l'amitié (aucune autre table dédiée)
    Un refus ou un retrait supprime simplement la ligne.
    """
    __tablename__ = "friend_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="users.id", index=True)
    addressee_id: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = Field(default=None)


class TradeRequest(SQLModel, table=True):
    """
    Placeholder : pose juste l'intention d'échanger entre deux amis.
    Le choix des cartes et l'échange lui-même seront ajoutés plus tard ;
    pour l'instant une ligne ne porte qu'un statut "pending" à faire
    disparaître (accepter/annuler) une fois vue.
    """
    __tablename__ = "trade_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="users.id", index=True)
    addressee_id: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)
