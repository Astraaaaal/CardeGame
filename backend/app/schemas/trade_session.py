"""
Schemas — session d'échange en direct.
"""

from datetime import datetime
from pydantic import BaseModel

from app.schemas.card import CardResponse


class TradeSessionItemOut(BaseModel):
    id: int
    owner_id: int
    item_type: str  # "card" | "resource"
    card: CardResponse | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    amount: int | None = None


class TradeSessionOut(BaseModel):
    id: int
    status: str
    other_user_id: int
    other_username: str
    other_display_name: str
    other_online: bool

    my_ready: bool
    other_ready: bool
    my_confirmed: bool
    other_confirmed: bool

    my_items: list[TradeSessionItemOut] = []
    other_items: list[TradeSessionItemOut] = []

    updated_at: datetime
    removed_items: list[str] = []  # message(s) d'objets invalidés lors de la dernière tentative d'exécution


class AddCardItemBody(BaseModel):
    user_card_id: str


class AddResourceItemBody(BaseModel):
    resource_id: str
    amount: int


class SetReadyBody(BaseModel):
    ready: bool
