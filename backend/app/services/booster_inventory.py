"""
Boosters possédés non ouverts — crédit (récompenses) et ouverture (dans la
boutique, avec la même animation qu'un achat) depuis ce solde.
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.booster import Booster
from app.models.booster_inventory import UserBoosterInventory
from app.services.pack_service import PackService

_pack_service = PackService()


async def grant(session: AsyncSession, user_id: int, booster_id: str, quantity: int = 1) -> None:
    row = await session.get(UserBoosterInventory, (user_id, booster_id))
    if not row:
        row = UserBoosterInventory(user_id=user_id, booster_id=booster_id, quantity=0)
    row.quantity += quantity
    session.add(row)


async def consume(session: AsyncSession, user_id: int, booster_id: str, quantity: int) -> None:
    row = await session.get(UserBoosterInventory, (user_id, booster_id))
    if not row or row.quantity < quantity:
        raise HTTPException(400, f"Tu ne possèdes que {row.quantity if row else 0} exemplaire(s) de ce booster.")
    row.quantity -= quantity
    session.add(row)


async def list_owned(session: AsyncSession, user_id: int) -> list[dict]:
    rows = (await session.execute(
        select(UserBoosterInventory).where(
            UserBoosterInventory.user_id == user_id, UserBoosterInventory.quantity > 0,
        )
    )).scalars().all()
    out = []
    for row in rows:
        booster = await session.get(Booster, row.booster_id)
        if not booster:
            continue
        out.append({
            "booster_id": booster.id, "booster_name": booster.name,
            "booster_cover_url": booster.cover_image_url or None, "quantity": row.quantity,
        })
    return out


async def open_owned(session: AsyncSession, user: User, booster_id: str, quantity: int) -> dict:
    if quantity < 1:
        raise HTTPException(400, "Quantité invalide.")

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
