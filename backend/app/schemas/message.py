"""
Schemas — messagerie (messages admin + cadeaux entre joueurs).
"""

from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.card import CardResponse


class MessageRewardItemOut(BaseModel):
    kind: str  # resource | booster | reroll | card
    name: str
    quantity: int = 1
    resource_id: str | None = None
    booster_id: str | None = None
    label: str | None = None  # bonus du booster
    card: CardResponse | None = None


class MessageOut(BaseModel):
    id: int
    sender_type: str  # "admin" | "player"
    sender_display_name: str  # "Administration" ou le pseudo de l'expéditeur
    subject: str
    body: str
    reward_resource_id: str | None = None
    reward_resource_name: str | None = None
    reward_amount: int | None = None
    reward_card: CardResponse | None = None
    reward_booster_id: str | None = None
    reward_booster_name: str | None = None
    reward_booster_cover_url: str | None = None
    reward_booster_qty: int | None = None
    reward_booster_label: str | None = None  # booster à bonus
    reward_reroll_label: str | None = None
    reward_reroll_qty: int | None = None
    reward_items: list[MessageRewardItemOut] = []
    has_reward: bool
    created_at: datetime
    read_at: datetime | None = None
    claimed_at: datetime | None = None
    claim_error: str | None = None


class SendGiftBody(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    subject: str = Field(default="Cadeau", max_length=100)
    body: str = Field(default="", max_length=2000)
    item_type: str = Field(pattern="^(card|resource|booster|reroll)$")
    user_card_id: str | None = None
    resource_id: str | None = None
    amount: int | None = None
    booster_id: str | None = None
    bonus_id: int | None = None  # booster à bonus (cf. UserBonusBooster)
    reroll_token_id: int | None = None


class SendAdminMessageBody(BaseModel):
    # Vide/absent = envoi à TOUS les joueurs.
    usernames: list[str] | None = None
    subject: str = Field(min_length=1, max_length=100)
    body: str = Field(default="", max_length=2000)
    reward_resource_id: str | None = None
    reward_amount: int | None = None
    # Récompenses multiples (ressource, booster, reroll, carte) — cf. message_rewards.py.
    rewards: list[dict] = Field(default_factory=list, max_length=20)


class SendAdminMessageResponse(BaseModel):
    sent_count: int
