"""
Routes publiques (côté joueurs connectés) — consulter la vitrine d'un autre
joueur et interagir avec ses cartes à échanger. L'édition de SA PROPRE
vitrine vit dans app/api/player.py (/api/player/showcase, /trade-listings).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.card import UserCard
from app.models.social import TradeListing
from app.schemas.showcase import ShowcaseResponse
from app.schemas.social import TradeRequestOut
from app.services.showcase_view import build_showcase_response
from app.services.wallet import get_balance, apply_delta
from app.services.trade_requests import create_trade_request

router = APIRouter()


@router.get("/{user_id}/showcase", response_model=ShowcaseResponse)
async def get_player_showcase(
    user_id: int,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Vitrine publique d'un joueur (avatar, cartes mises en avant, cartes à échanger)."""
    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(404, "Joueur introuvable.")
    return await build_showcase_response(session, target)


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
    if buyer.id == user_id:
        raise HTTPException(400, "Tu ne peux pas acheter ta propre carte.")

    listing = await session.get(TradeListing, (user_id, slot))
    if not listing or listing.mode != "buy_now":
        raise HTTPException(404, "Annonce introuvable.")

    card = await session.get(UserCard, listing.user_card_id)
    if not card or card.user_id != user_id:
        # La carte a changé de main ou a été recyclée depuis : annonce caduque.
        await session.delete(listing)
        await session.commit()
        raise HTTPException(409, "Cette carte n'est plus disponible.")

    have = await get_balance(session, buyer, listing.resource_id)
    if have < listing.price:
        raise HTTPException(400, f"Solde insuffisant ({have}/{listing.price}).")

    seller = await session.get(User, user_id)

    await apply_delta(session, buyer, listing.resource_id, -listing.price)
    await apply_delta(session, seller, listing.resource_id, listing.price)

    card.user_id = buyer.id
    session.add(card)
    buyer.total_cards += 1
    seller.total_cards = max(0, seller.total_cards - 1)
    session.add(buyer)
    session.add(seller)

    await session.delete(listing)
    await session.commit()

    return await build_showcase_response(session, seller)


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
