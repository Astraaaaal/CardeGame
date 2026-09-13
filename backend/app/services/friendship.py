"""
Vérification d'amitié — factorisé pour être réutilisé par app/api/friends.py
ET app/services/trade_policy.py (qui ne peut pas importer depuis un module API
sans créer une dépendance circulaire).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_

from app.models.social import FriendRequest


async def friendship_between(session: AsyncSession, a: int, b: int) -> FriendRequest | None:
    return (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(
                and_(FriendRequest.requester_id == a, FriendRequest.addressee_id == b),
                and_(FriendRequest.requester_id == b, FriendRequest.addressee_id == a),
            ),
        )
    )).scalar_one_or_none()
