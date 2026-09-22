"""
Portefeuille générique — lit/modifie le solde d'un joueur pour une ressource
quelconque. "coins" est un id de ressource réservé qui ne passe PAS par
UserResource : il reste routé vers le champ natif User.coins, pour ne pas
perturber tout le code existant (récompense quotidienne, affichage, etc.)
qui en dépend directement. Toute autre ressource passe par UserResource.

Les variations passent par une requête SQL atomique (« solde = solde + delta »)
et non par une relecture suivie d'une réécriture : deux actions simultanées
(un achat pendant qu'un autre joueur nous paie, par exemple) ne peuvent pas
s'écraser, et un retrait n'est jamais appliqué s'il rendait le solde négatif.
"""

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.models.economy import Resource, UserResource
from app.models.user import User

COINS_ID = "coins"

_users = User.__table__
_user_resources = UserResource.__table__


async def get_balance(session: AsyncSession, user: User, resource_id: str) -> int:
    if resource_id == COINS_ID:
        return user.coins
    row = await session.get(UserResource, (user.id, resource_id))
    return row.amount if row else 0


async def _not_enough(session: AsyncSession, resource_id: str, missing: int) -> HTTPException:
    if resource_id == COINS_ID:
        name = "pièces"
    else:
        resource = await session.get(Resource, resource_id)
        name = (resource.name if resource else resource_id).lower()
    return HTTPException(400, f"Pas assez de {name} : il t'en manque {missing:,}.".replace(",", " "))


async def require_balance(session: AsyncSession, user: User, resource_id: str, amount: int) -> None:
    """400 lisible si le joueur n'a pas `amount` de la ressource."""
    have = await get_balance(session, user, resource_id)
    if have < amount:
        raise await _not_enough(session, resource_id, amount - have)


async def apply_delta(session: AsyncSession, user: User, resource_id: str, delta: int) -> int:
    """Applique `delta` (positif ou négatif) au solde et retourne le nouveau solde.
    Un retrait supérieur au solde est refusé (400) sans rien modifier."""
    if not delta:
        return await get_balance(session, user, resource_id)
    await session.flush()  # changements en attente écrits avant la requête atomique

    if resource_id == COINS_ID:
        stmt = update(_users).where(_users.c.id == user.id)
        if delta < 0:
            stmt = stmt.where(_users.c.coins + delta >= 0)
        new = (await session.execute(
            stmt.values(coins=_users.c.coins + delta).returning(_users.c.coins)
        )).scalar_one_or_none()
        if new is None:
            current = (await session.execute(select(_users.c.coins).where(_users.c.id == user.id))).scalar() or 0
            raise await _not_enough(session, resource_id, -delta - current)
        set_committed_value(user, "coins", new)
        return new

    key = (_user_resources.c.user_id == user.id) & (_user_resources.c.resource_id == resource_id)
    if delta < 0:
        new = (await session.execute(
            update(_user_resources).where(key, _user_resources.c.amount + delta >= 0)
            .values(amount=_user_resources.c.amount + delta).returning(_user_resources.c.amount)
        )).scalar_one_or_none()
        if new is None:
            current = (await session.execute(select(_user_resources.c.amount).where(key))).scalar() or 0
            raise await _not_enough(session, resource_id, -delta - current)
    else:
        dialect = postgresql if session.bind.dialect.name == "postgresql" else sqlite
        new = (await session.execute(
            dialect.insert(_user_resources)
            .values(user_id=user.id, resource_id=resource_id, amount=delta)
            .on_conflict_do_update(
                index_elements=[_user_resources.c.user_id, _user_resources.c.resource_id],
                set_={"amount": _user_resources.c.amount + delta},
            )
            .returning(_user_resources.c.amount)
        )).scalar_one()

    # Garde l'objet déjà chargé dans la session aligné sur la base.
    row = session.identity_map.get(session.identity_key(UserResource, (user.id, resource_id)))
    if row is not None:
        set_committed_value(row, "amount", new)
    return new
