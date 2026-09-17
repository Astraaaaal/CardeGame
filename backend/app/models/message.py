"""
Messagerie — messages de l'administration (individuels ou broadcast, avec
récompense optionnelle à récupérer) et cadeaux entre joueurs (carte ou
ressource, envoyés par ce même mécanisme de boîte de réception).
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import JSON, Column, ForeignKey, String
from sqlmodel import SQLModel, Field


class Message(SQLModel, table=True):
    """
    Une ligne = un message pour UN destinataire (un envoi "à tous" crée une
    ligne par joueur — plus simple qu'une table de lecture séparée, au prix
    d'un peu de duplication, largement acceptable à cette échelle).

    - sender_type = "admin"  : sender_user_id est NULL, affiché "Administration".
    - sender_type = "player" : cadeau envoyé par un autre joueur.
    Récompense optionnelle, au plus UNE des deux formes à la fois :
    - reward_resource_id + reward_amount : ressource (déjà débitée chez
      l'expéditeur pour un cadeau joueur ; créée ex nihilo pour un message admin).
    - reward_card_id : une carte précise (cadeau joueur uniquement pour l'instant) ;
      reste chez l'expéditeur jusqu'à la récupération (revalidée à ce moment,
      même logique défensive que la session d'échange).
    - reward_booster_id + reward_booster_qty : booster(s) non ouvert(s)
      (cadeau joueur uniquement) ; déjà débités de l'inventaire de
      l'expéditeur, crédités à celui du destinataire à la récupération.
      reward_booster_bonus (optionnel) : bonus d'un booster acheté via une offre
      {force_min_rarity_id, rarity_weight_multiplier, label}, conservé.
    - reward_reroll : rerolls de l'inventaire {label, offer_id, règles, quantity}.
    """
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    sender_type: str = Field(max_length=10)  # "admin" | "player"
    sender_user_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    recipient_user_id: int = Field(foreign_key="users.id", index=True)

    subject: str = Field(max_length=100)
    body: str = Field(default="", max_length=2000)

    reward_resource_id: Optional[str] = Field(default=None, foreign_key="resources.id", max_length=30)
    reward_amount: Optional[int] = Field(default=None)
    reward_card_id: Optional[str] = Field(
        default=None, sa_column=Column(String, ForeignKey("user_cards.id", ondelete="SET NULL")),
    )
    reward_booster_id: Optional[str] = Field(default=None, foreign_key="boosters.id", max_length=30)
    reward_booster_qty: Optional[int] = Field(default=None)
    reward_booster_bonus: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    reward_reroll: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    # Messages admin : liste de récompenses (cf. app/services/message_rewards.py).
    reward_items: Optional[list] = Field(default=None, sa_column=Column(JSON, nullable=True))

    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = Field(default=None)
    claimed_at: Optional[datetime] = Field(default=None)
    # Rempli si la récompense n'a pas pu être livrée à la récupération
    # (carte plus disponible) — le message reste consultable, juste sans gain.
    claim_error: Optional[str] = Field(default=None, max_length=200)
