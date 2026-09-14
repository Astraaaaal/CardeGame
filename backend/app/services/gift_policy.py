"""
Politique de réception des cadeaux — définie par le DESTINATAIRE dans ses
paramètres (User.gift_policy) : qui a le droit de lui envoyer un cadeau
(carte ou ressource). Même forme que trade_policy.py.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.social import CloseFriend
from app.services.friendship import friendship_between


async def can_send_gift(session: AsyncSession, sender_id: int, target: User) -> bool:
    policy = target.gift_policy
    if policy == "none":
        return False
    if policy == "everyone":
        return True
    if policy == "close_friends":
        return await session.get(CloseFriend, (target.id, sender_id)) is not None
    return bool(await friendship_between(session, sender_id, target.id))
