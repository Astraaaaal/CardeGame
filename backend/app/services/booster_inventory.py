"""
Boosters possédés non ouverts — crédit (récompenses, achat "garder pour
plus tard") et ouverture (même animation qu'un achat) depuis ce solde.

Deux stocks : les boosters simples (UserBoosterInventory, un compteur par
booster) et les boosters achetés via une offre du shop à ressources, qui
gardent leur bonus (UserBonusBooster, une ligne par bonus identique).
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.booster import Booster
from app.models.booster_inventory import UserBoosterInventory, UserBonusBooster
from app.models.economy import Resource
from app.services.pack_service import PackService
from app.services.wallet import get_balance

_pack_service = PackService()


async def grant(session: AsyncSession, user_id: int, booster_id: str, quantity: int = 1) -> None:
    row = await session.get(UserBoosterInventory, (user_id, booster_id))
    if not row:
        row = UserBoosterInventory(user_id=user_id, booster_id=booster_id, quantity=0)
    row.quantity += quantity
    session.add(row)


async def grant_bonus(
    session: AsyncSession, user_id: int, booster_id: str,
    force_min_rarity_id: str | None, rarity_weight_multiplier: float | None, label: str, quantity: int = 1,
) -> None:
    """Crédite un booster à bonus ; sans bonus, retombe sur le stock simple."""
    if not force_min_rarity_id and not rarity_weight_multiplier:
        await grant(session, user_id, booster_id, quantity)
        return
    row = (await session.execute(
        select(UserBonusBooster).where(
            UserBonusBooster.user_id == user_id,
            UserBonusBooster.booster_id == booster_id,
            UserBonusBooster.force_min_rarity_id == force_min_rarity_id,
            UserBonusBooster.rarity_weight_multiplier == rarity_weight_multiplier,
        )
    )).scalars().first()
    if not row:
        row = UserBonusBooster(
            user_id=user_id, booster_id=booster_id, force_min_rarity_id=force_min_rarity_id,
            rarity_weight_multiplier=rarity_weight_multiplier, label=label, quantity=0,
        )
    row.quantity += quantity
    session.add(row)


async def consume(session: AsyncSession, user_id: int, booster_id: str, quantity: int) -> None:
    row = await session.get(UserBoosterInventory, (user_id, booster_id))
    if not row or row.quantity < quantity:
        raise HTTPException(400, f"Tu ne possèdes que {row.quantity if row else 0} exemplaire(s) de ce booster.")
    row.quantity -= quantity
    session.add(row)


async def consume_bonus(session: AsyncSession, user_id: int, bonus_id: int, quantity: int) -> UserBonusBooster:
    """Retire des boosters à bonus du stock (cadeau). Ne commit pas."""
    row = await session.get(UserBonusBooster, bonus_id)
    if not row or row.user_id != user_id or row.quantity < quantity:
        owned = row.quantity if row and row.user_id == user_id else 0
        raise HTTPException(400, f"Tu ne possèdes que {owned} exemplaire(s) de ce booster.")
    row.quantity -= quantity
    session.add(row)
    return row


async def list_owned(session: AsyncSession, user_id: int) -> list[dict]:
    out = []
    rows = (await session.execute(
        select(UserBoosterInventory).where(
            UserBoosterInventory.user_id == user_id, UserBoosterInventory.quantity > 0,
        )
    )).scalars().all()
    for row in rows:
        booster = await session.get(Booster, row.booster_id)
        if not booster:
            continue
        out.append({
            "booster_id": booster.id, "booster_name": booster.name,
            "booster_cover_url": booster.cover_image_url or None, "quantity": row.quantity,
            "bonus_id": None, "bonus_label": None,
        })

    bonus_rows = (await session.execute(
        select(UserBonusBooster).where(UserBonusBooster.user_id == user_id, UserBonusBooster.quantity > 0)
        .order_by(UserBonusBooster.id)
    )).scalars().all()
    for row in bonus_rows:
        booster = await session.get(Booster, row.booster_id)
        if not booster:
            continue
        out.append({
            "booster_id": booster.id, "booster_name": booster.name,
            "booster_cover_url": booster.cover_image_url or None, "quantity": row.quantity,
            "bonus_id": row.id, "bonus_label": row.label or None,
        })
    return out


async def buy_to_inventory(session: AsyncSession, user: User, booster_id: str, quantity: int) -> dict:
    """Achat classique d'un booster (même prix/réductions), crédité à l'inventaire au lieu d'être ouvert."""
    booster, _, total_price = await _pack_service.charge(session, user.id, booster_id, quantity)
    await grant(session, user.id, booster.id, quantity)
    await session.commit()
    resource = await session.get(Resource, booster.resource_id)
    return {
        "booster_id": booster.id,
        "booster_name": booster.name,
        "quantity": quantity,
        "total_cost": total_price,
        "resource_id": booster.resource_id,
        "resource_name": resource.name if resource else booster.resource_id,
        "new_balance": await get_balance(session, user, booster.resource_id),
    }


async def open_owned(
    session: AsyncSession, user: User, booster_id: str, quantity: int, bonus_id: int | None = None,
) -> dict:
    if quantity < 1:
        raise HTTPException(400, "Quantité invalide.")

    force_min_rarity_id = None
    rarity_weight_multiplier = None
    if bonus_id is not None:
        row = await session.get(UserBonusBooster, bonus_id)
        if not row or row.user_id != user.id or row.booster_id != booster_id or row.quantity < quantity:
            raise HTTPException(400, f"Tu ne possèdes que {row.quantity if row and row.user_id == user.id else 0} exemplaire(s) de ce booster.")
        force_min_rarity_id = row.force_min_rarity_id
        rarity_weight_multiplier = row.rarity_weight_multiplier
    else:
        row = await session.get(UserBoosterInventory, (user.id, booster_id))
        if not row or row.quantity < quantity:
            raise HTTPException(400, f"Tu ne possèdes que {row.quantity if row else 0} exemplaire(s) de ce booster.")

    booster = await session.get(Booster, booster_id)
    if not booster:
        raise HTTPException(404, "Booster introuvable.")

    row.quantity -= quantity
    session.add(row)

    all_packs_response, total_new_cards = await _pack_service.generate_and_persist_packs(
        session, user.id, booster, quantity,
        force_min_rarity_id=force_min_rarity_id,
        rarity_weight_multiplier=rarity_weight_multiplier,
    )
    user.total_cards += total_new_cards
    user.packs_opened += quantity
    await session.commit()

    return {
        "packs": all_packs_response,
        "total_cost": 0,
        "remaining_coins": user.coins,
        "resource_id": "",
        "resource_name": "",
        "new_balance": 0,
    }
