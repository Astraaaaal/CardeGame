"""Favoris et verrou d'un exemplaire : effacés quand il change de propriétaire."""

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import UserCard
from app.models.favorite import FavoriteCard


async def release(session: AsyncSession, card: UserCard) -> None:
    """À appeler quand la carte passe à un autre joueur (échange, cadeau, achat). Ne commit pas."""
    card.locked = False
    await session.execute(delete(FavoriteCard).where(FavoriteCard.user_card_id == card.id))
