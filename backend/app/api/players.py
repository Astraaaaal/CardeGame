"""
Routes publiques (côté joueurs connectés) — consulter la vitrine d'un autre
joueur et interagir avec ses cartes à échanger. L'édition de SA PROPRE
vitrine vit dans app/api/player.py (/api/player/showcase, /trade-listings).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.services import account_email, expeditions
from app.models.card import UserCard
from app.models.social import TradeListing
from app.schemas.showcase import ShowcaseResponse
from app.schemas.social import TradeRequestOut
from app.services.showcase_view import build_showcase_response
from app.services.ranking import refresh_all_best_ranks
from app.services.wallet import get_balance, apply_delta
from app.services.trade_requests import create_trade_request
from app.services import favorites
from app.services import unlocks
from app.services import trade_tax
from app.services.wallet import COINS_ID

router = APIRouter()


@router.get("/{user_id}/showcase", response_model=ShowcaseResponse)
async def get_player_showcase(
    user_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Vitrine publique d'un joueur (avatar, cartes mises en avant, cartes à échanger)."""
    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(404, "Joueur introuvable.")
    return await build_showcase_response(session, target, viewer_id=user.id)


@router.post(
    "/{user_id}/trade-listings/{slot}/buy", response_model=ShowcaseResponse,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def buy_trade_listing(
    user_id: int,
    slot: int,
    buyer: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Achat direct d'une carte listée en mode "buy_now" : transfert immédiat
    de la ressource (vendeur <- acheteur) et de la carte (vendeur -> acheteur).
    """
    await unlocks.require(session, buyer, "listings")
    account_email.require_verified_email(buyer)
    if buyer.id == user_id:
        raise HTTPException(400, "Tu ne peux pas acheter ta propre carte.")

    # Annonce puis carte relues et verrouillées jusqu'au commit : deux acheteurs
    # simultanés ne peuvent pas payer tous les deux la même carte.
    listing = (await session.execute(
        select(TradeListing).where(TradeListing.user_id == user_id, TradeListing.slot == slot)
        .with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not listing or listing.mode != "buy_now":
        raise HTTPException(404, "Annonce introuvable.")

    card = (await session.execute(
        select(UserCard).where(UserCard.id == listing.user_card_id)
        .with_for_update().execution_options(populate_existing=True)
    )).scalar_one_or_none()
    if not card or card.user_id != user_id:
        # La carte a changé de main ou a été recyclée depuis : annonce caduque.
        await session.delete(listing)
        await session.commit()
        raise HTTPException(409, "Cette carte n'est plus disponible.")
    await expeditions.ensure_not_on_expedition(session, [card.id])

    seller = await session.get(User, user_id)
    tax = await trade_tax.tax_for_items(
        session, await trade_tax.rate_for(session, buyer, seller), [{"type": "card", "card": card}],
    )
    have = await get_balance(session, buyer, listing.resource_id)
    need = listing.price + (tax if listing.resource_id == COINS_ID else 0)
    if have < need:
        raise HTTPException(400, f"Il te faut {need} {'pièces' if listing.resource_id == COINS_ID else ''} (prix + taxe {tax}) : il t'en manque {need - have}.".replace("  ", " "))
    if listing.resource_id != COINS_ID and await get_balance(session, buyer, COINS_ID) < tax:
        raise HTTPException(400, f"Il te faut {tax} pièces pour la taxe de cet achat.")

    await apply_delta(session, buyer, listing.resource_id, -listing.price)
    await apply_delta(session, seller, listing.resource_id, listing.price)
    await apply_delta(session, buyer, COINS_ID, -tax)

    card.user_id = buyer.id
    await favorites.release(session, card)
    session.add(card)
    buyer.total_cards += 1
    session.add(buyer)
    # Compteur du vendeur modifié en base directement : il peut agir au même moment.
    users = User.__table__
    await session.execute(update(users).where(users.c.id == seller.id).values(
        total_cards=case((users.c.total_cards > 0, users.c.total_cards - 1), else_=0),
    ))

    await session.delete(listing)
    await refresh_all_best_ranks(session)
    await session.commit()

    return await build_showcase_response(session, seller, viewer_id=buyer.id)


@router.post(
    "/{user_id}/trade-listings/{slot}/propose", response_model=TradeRequestOut, status_code=201,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def propose_on_trade_listing(
    user_id: int,
    slot: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Réagit à une annonce en mode "offer" (prix indicatif) : crée une demande
    d'échange, comme le bouton générique "proposer un échange" entre amis.
    """
    if user.id == user_id:
        raise HTTPException(400, "Tu ne peux pas proposer un échange sur ta propre carte.")

    listing = await session.get(TradeListing, (user_id, slot))
    if not listing or listing.mode != "offer":
        raise HTTPException(404, "Annonce introuvable.")

    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(404, "Joueur introuvable.")

    req = await create_trade_request(session, user, target)
    return TradeRequestOut(
        id=req.id, user_id=target.id, username=target.username,
        display_name=target.display_name, created_at=req.created_at,
    )
