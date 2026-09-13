"""
Politique de réception des demandes d'échange — définie par le DESTINATAIRE
dans ses paramètres (User.trade_request_policy) : qui a le droit de lui en
envoyer une (bouton générique "proposer un échange" ou clic sur une carte
à échanger listée en mode "offer").
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.social import CloseFriend
from app.services.friendship import friendship_between


async def can_send_trade_request(session: AsyncSession, requester_id: int, target: User) -> bool:
    policy = target.trade_request_policy
    if policy == "none":
        return False
    if policy == "everyone":
        return True
    if policy == "close_friends":
        return await session.get(CloseFriend, (target.id, requester_id)) is not None
    # "friends" (valeur par défaut) et toute valeur inconnue → le plus prudent après "none"
    return bool(await friendship_between(session, requester_id, target.id))
