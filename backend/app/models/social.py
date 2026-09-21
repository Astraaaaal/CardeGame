"""
Modèles social — demandes d'ami et demandes d'échange (placeholder).
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, ForeignKey, Integer
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
    `seen` : sert au popup de notification (cf. app/api/friends.py) — passe
    à True dès que le destinataire a vu la demande, pour ne la signaler qu'une fois.
    """
    __tablename__ = "trade_requests"

    id: Optional[int] = Field(default=None, primary_key=True)
    requester_id: int = Field(foreign_key="users.id", index=True)
    addressee_id: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default="pending", max_length=20)
    seen: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CloseFriend(SQLModel, table=True):
    """
    Marquage à sens unique : `user_id` considère `friend_user_id` comme un
    ami proche (comme les "Close Friends" d'Instagram — pas besoin que
    l'autre soit d'accord). Suppose une amitié déjà établie entre les deux ;
    sert de filtre pour `User.trade_request_policy == "close_friends"`.
    """
    __tablename__ = "close_friends"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    friend_user_id: int = Field(foreign_key="users.id", primary_key=True)


class FriendGroup(SQLModel, table=True):
    """Groupe personnalisé créé par un joueur pour organiser sa liste d'amis
    (ex: "Guilde", "École") — propriété à sens unique, comme CloseFriend."""
    __tablename__ = "friend_groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=30)
    # Ordre d'affichage choisi par le joueur (flèches ↑ ↓).
    position: int = Field(default=0)


class FriendGroupMember(SQLModel, table=True):
    """Appartenance d'un ami à un groupe — un ami peut être dans plusieurs
    groupes à la fois (pas de contrainte d'exclusivité)."""
    __tablename__ = "friend_group_members"

    # ON DELETE CASCADE : supprimer un groupe vide ses membres sans étape manuelle.
    group_id: int = Field(
        sa_column=Column(Integer, ForeignKey("friend_groups.id", ondelete="CASCADE"), primary_key=True),
    )
    friend_user_id: int = Field(foreign_key="users.id", primary_key=True)


class TradeListing(SQLModel, table=True):
    """
    Une carte possédée mise en avant "à échanger" sur la vitrine, avec un
    prix dans une ressource au choix. 3 emplacements par joueur (indépendants
    des 3 cartes cosmétiques de la vitrine — une même carte peut apparaître
    dans les deux).
    - mode = "buy_now" : achat direct — la carte change de main immédiatement
      contre le prix affiché (cf. app/api/players.py::buy_trade_listing).
    - mode = "offer"   : prix indicatif — un clic crée juste une TradeRequest
      (nécessite d'être amis, comme le reste du système d'échange).
    """
    __tablename__ = "trade_listings"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    slot: int = Field(primary_key=True)  # 0, 1, 2
    user_card_id: str = Field(foreign_key="user_cards.id")
    resource_id: str = Field(foreign_key="resources.id", max_length=30)
    price: int = Field(default=0)
    mode: str = Field(max_length=20)  # "buy_now" | "offer"
