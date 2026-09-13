"""
Modèle User — Joueur avec ses stats et credentials.
"""

from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.card import UserCard
    from app.models.token import RefreshToken


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=20, unique=True, index=True)
    display_name: str = Field(max_length=20)
    password_hash: str = Field(max_length=256)

    # Économie
    coins: int = Field(default=500)

    # Stats
    packs_opened: int = Field(default=0)
    total_cards: int = Field(default=0)

    # Streak
    login_streak: int = Field(default=0)
    last_daily_claim: Optional[date] = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = Field(default=None)
    # Mis à jour (au plus une fois/minute) à chaque requête authentifiée —
    # sert à dériver un statut "en ligne" approximatif (cf. core/dependencies.py).
    last_seen: Optional[datetime] = Field(default=None)

    # Vitrine publique (consultable par les autres joueurs) : avatar = un
    # personnage possédé, + jusqu'à 3 cartes possédées mises en avant.
    # D'autres infos (badges, etc.) pourront s'ajouter ici plus tard.
    avatar_character_id: Optional[str] = Field(default=None, foreign_key="characters.id", max_length=30)
    showcase_card_1_id: Optional[str] = Field(default=None, foreign_key="user_cards.id")
    showcase_card_2_id: Optional[str] = Field(default=None, foreign_key="user_cards.id")
    showcase_card_3_id: Optional[str] = Field(default=None, foreign_key="user_cards.id")

    # Paramètres sociaux — contrôlent qui peut t'envoyer une demande d'ami ou
    # d'échange, et si une nouvelle demande d'échange déclenche un popup.
    allow_friend_requests: bool = Field(default=True)
    # "everyone" | "friends" | "close_friends" | "none"
    trade_request_policy: str = Field(default="friends", max_length=20)
    trade_request_popup_enabled: bool = Field(default=True)

    # Relations
    # foreign_keys explicite : les colonnes showcase_card_*_id ajoutent un
    # second chemin de FK entre users et user_cards (dans l'autre sens), donc
    # SQLAlchemy ne peut plus déduire seul quelle colonne joindre pour "cards".
    cards: List["UserCard"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"foreign_keys": "UserCard.user_id"},
    )
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")
