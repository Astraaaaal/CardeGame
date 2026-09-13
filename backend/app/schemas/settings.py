"""
Schemas — paramètres sociaux du joueur (demandes d'ami, demandes d'échange).
"""

from typing import Literal
from pydantic import BaseModel

TradeRequestPolicy = Literal["everyone", "friends", "close_friends", "none"]


class PlayerSettings(BaseModel):
    allow_friend_requests: bool
    trade_request_policy: TradeRequestPolicy
    trade_request_popup_enabled: bool


class UpdatePlayerSettings(BaseModel):
    allow_friend_requests: bool | None = None
    trade_request_policy: TradeRequestPolicy | None = None
    trade_request_popup_enabled: bool | None = None
