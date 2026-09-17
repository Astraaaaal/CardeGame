"""
Rerolls gardés en inventaire : crédit à l'achat (règles figées) et utilisation
sur une carte possédée.
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.card import UserCard
from app.models.economy import ShopOffer
from app.models.reroll_inventory import UserRerollToken
from app.models.user import User
from app.services.card_view import build_card_response
from app.services.ranking import refresh_all_best_ranks
from app.services.reroll import apply_reroll, reroll_axes

_RULE_FIELDS = ("reroll_rarity", "reroll_quality", "reroll_specialty", "reroll_jewelry", "reroll_power", "reroll_mode")


async def grant(session: AsyncSession, user_id: int, offer: ShopOffer, quantity: int) -> None:
    """Crédite `quantity` rerolls avec les règles actuelles de l'offre. Ne commit pas."""
    query = select(UserRerollToken).where(
        UserRerollToken.user_id == user_id, UserRerollToken.offer_id == offer.id,
        *(getattr(UserRerollToken, f) == getattr(offer, f) for f in _RULE_FIELDS),
    )
    row = (await session.execute(query)).scalars().first()
    if not row:
        row = UserRerollToken(
            user_id=user_id, offer_id=offer.id, label=offer.name, quantity=0,
            **{f: getattr(offer, f) for f in _RULE_FIELDS},
        )
    row.quantity += quantity
    session.add(row)


def to_out(row: UserRerollToken) -> dict:
    return {
        "id": row.id, "offer_id": row.offer_id, "label": row.label, "quantity": row.quantity,
        "axes": reroll_axes(row), "reroll_power": row.reroll_power, "reroll_mode": row.reroll_mode,
    }


async def list_owned(session: AsyncSession, user_id: int) -> list[dict]:
    rows = (await session.execute(
        select(UserRerollToken).where(UserRerollToken.user_id == user_id, UserRerollToken.quantity > 0)
        .order_by(UserRerollToken.id)
    )).scalars().all()
    return [to_out(r) for r in rows]


async def use(session: AsyncSession, user: User, token_id: int, card_id: str) -> dict:
    token = (await session.execute(
        select(UserRerollToken).where(UserRerollToken.id == token_id).with_for_update()
    )).scalar_one_or_none()
    if not token or token.user_id != user.id or token.quantity < 1:
        raise HTTPException(400, "Tu ne possèdes plus ce reroll.")
    card = (await session.execute(
        select(UserCard).where(UserCard.id == card_id, UserCard.user_id == user.id)
    )).scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Carte introuvable.")

    previous_card = await build_card_response(session, card)
    await apply_reroll(session, card, token)
    token.quantity -= 1
    session.add(token)
    await session.flush()
    new_card = await build_card_response(session, card)
    await refresh_all_best_ranks(session)
    await session.commit()
    return {
        "message": f"« {token.label} » utilisé !",
        "previous_card": previous_card,
        "card": new_card,
        "token": to_out(token),
    }
