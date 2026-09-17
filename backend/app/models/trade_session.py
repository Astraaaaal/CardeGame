"""
Session d'échange en direct (façon Warframe) — deux joueurs négocient en
temps réel (polling côté client), chacun ajoute des cartes et/ou des
ressources de son côté, puis un double "prêt" + double "confirmer" avant
exécution atomique du transfert.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, ForeignKey, String
from sqlmodel import SQLModel, Field

# negotiating -> (les deux "ready") -> confirming -> (les deux "confirmed") -> completed
# à tout moment avant "completed" : cancelled (un des deux annule) ou expired (inactivité)
STATUS_NEGOTIATING = "negotiating"
STATUS_CONFIRMING = "confirming"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"

ACTIVE_STATUSES = (STATUS_NEGOTIATING, STATUS_CONFIRMING)

MAX_ITEMS_PER_SIDE = 12
EXPIRE_AFTER_MINUTES = 20
# Un des deux joueurs n'a plus donné signe de vie (cf. User.last_seen) depuis :
ABSENT_EXPIRE_MINUTES = 5


class TradeSession(SQLModel, table=True):
    __tablename__ = "trade_sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_a_id: int = Field(foreign_key="users.id", index=True)
    user_b_id: int = Field(foreign_key="users.id", index=True)
    status: str = Field(default=STATUS_NEGOTIATING, max_length=20)

    ready_a: bool = Field(default=False)
    ready_b: bool = Field(default=False)
    confirmed_a: bool = Field(default=False)
    confirmed_b: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TradeSessionItem(SQLModel, table=True):
    """Un objet posé par l'un des deux joueurs dans une session en cours.
    `item_type` :
    - "card"     : une carte précise (user_card_id)
    - "resource" : une quantité d'une ressource ("coins" compris, cf. wallet.py)
    - "booster"  : des boosters non ouverts (booster_id + amount, bonus_id si
                   ce sont des boosters à bonus, cf. booster_inventory.py)
    - "reroll"   : des rerolls de l'inventaire (reroll_token_id + amount)"""
    __tablename__ = "trade_session_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="trade_sessions.id", index=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    item_type: str = Field(max_length=10)  # "card" | "resource"

    # ON DELETE SET NULL : si la carte disparaît par un autre biais (recyclage,
    # etc.) pendant qu'elle est référencée par un item (même d'une session déjà
    # terminée), on ne veut pas bloquer cette suppression — l'item redevient
    # juste orphelin (filtré à l'affichage, traité comme invalide à l'exécution).
    user_card_id: Optional[str] = Field(
        default=None, sa_column=Column(String, ForeignKey("user_cards.id", ondelete="SET NULL")),
    )
    resource_id: Optional[str] = Field(default=None, foreign_key="resources.id", max_length=30)
    # Quantité : ressource, boosters ou rerolls.
    amount: Optional[int] = Field(default=None)
    booster_id: Optional[str] = Field(default=None, max_length=30)
    bonus_id: Optional[int] = Field(default=None)
    reroll_token_id: Optional[int] = Field(default=None)
