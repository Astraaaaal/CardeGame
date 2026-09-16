"""
Schemas — amis, demandes d'ami, demandes d'échange (placeholder).
"""

from datetime import datetime
from pydantic import BaseModel, Field


class FriendOut(BaseModel):
    user_id: int
    username: str
    display_name: str
    online: bool
    last_seen: datetime | None = None
    close_friend: bool = False
    group_ids: list[int] = []


class FriendGroupOut(BaseModel):
    id: int
    name: str


class FriendGroupBody(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class SendFriendRequestBody(BaseModel):
    username: str = Field(min_length=1, max_length=20)


class FriendRequestOut(BaseModel):
    id: int
    user_id: int  # l'AUTRE joueur impliqué dans la demande
    username: str
    display_name: str
    created_at: datetime


class FriendRequestsResponse(BaseModel):
    incoming: list[FriendRequestOut] = []
    outgoing: list[FriendRequestOut] = []


class TradeRequestOut(BaseModel):
    id: int
    user_id: int  # l'AUTRE joueur impliqué
    username: str
    display_name: str
    created_at: datetime


class TradeRequestsResponse(BaseModel):
    incoming: list[TradeRequestOut] = []
    outgoing: list[TradeRequestOut] = []


class TradePulseOut(BaseModel):
    """État condensé interrogé en continu par le client (échange lancé,
    nouvelles demandes à afficher, listes à rafraîchir)."""
    active_session_id: int | None = None
    active_other_display_name: str | None = None
    incoming_unseen: list[TradeRequestOut] = []
    incoming_ids: list[int] = []
    outgoing_ids: list[int] = []


class SendTradeRequestBody(BaseModel):
    username: str = Field(min_length=1, max_length=20)
