"""
Portefeuille générique — lit/modifie le solde d'un joueur pour une ressource
quelconque. "coins" est un id de ressource réservé qui ne passe PAS par
UserResource : il reste routé vers le champ natif User.coins, pour ne pas
perturber tout le code existant (récompense quotidienne, affichage, etc.)
qui en dépend directement. Toute autre ressource passe par UserResource.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.economy import UserResource

COINS_ID = "coins"


async def get_balance(session: AsyncSession, user: User, resource_id: str) -> int:
    if resource_id == COINS_ID:
        return user.coins
    row = await session.get(UserResource, (user.id, resource_id))
    return row.amount if row else 0


async def require_balance(session: AsyncSession, user: User, resource_id: str, amount: int) -> None:
    """400 lisible si le joueur n'a pas `amount` de la ressource."""
    have = await get_balance(session, user, resource_id)
    if have < amount:
        from fastapi import HTTPException
        from app.models.economy import Resource
        if resource_id == COINS_ID:
            name = "pièces"
        else:
            resource = await session.get(Resource, resource_id)
            name = (resource.name if resource else resource_id).lower()
        raise HTTPException(400, f"Pas assez de {name} : il t'en manque {amount - have:,}.".replace(",", " "))


async def apply_delta(session: AsyncSession, user: User, resource_id: str, delta: int) -> int:
    """Applique `delta` (positif ou négatif) au solde et retourne le nouveau solde."""
    if resource_id == COINS_ID:
        user.coins += delta
        return user.coins
    row = await session.get(UserResource, (user.id, resource_id))
    if not row:
        row = UserResource(user_id=user.id, resource_id=resource_id, amount=0)
        session.add(row)
    row.amount += delta
    return row.amount
