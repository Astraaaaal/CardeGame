"""
Construction d'un ShowcaseResponse à partir d'un User — factorisé pour être
réutilisé par la route publique (voir un joueur) et la route d'édition (moi).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import Resource
from app.models.social import TradeListing
from app.schemas.showcase import ShowcaseResponse, AvatarInfo, TradeListingOut
from app.services.card_view import build_card_response


async def build_showcase_response(session: AsyncSession, target: User) -> ShowcaseResponse:
    avatar = None
    if target.avatar_character_id:
        char = await session.get(Character, target.avatar_character_id)
        if char:
            avatar = AvatarInfo(character_id=char.id, character_name=char.name, image_url=char.image_url)

    cards = []
    for slot_id in (target.showcase_card_1_id, target.showcase_card_2_id, target.showcase_card_3_id):
        if not slot_id:
            continue
        card = await session.get(UserCard, slot_id)
        # Re-vérifie l'appartenance : la carte a pu être recyclée depuis.
        if card and card.user_id == target.id:
            cards.append(await build_card_response(session, card))

    listings_rows = (await session.execute(
        select(TradeListing).where(TradeListing.user_id == target.id).order_by(TradeListing.slot)
    )).scalars().all()
    trade_listings = []
    for listing in listings_rows:
        card = await session.get(UserCard, listing.user_card_id)
        # Comme pour la vitrine cosmétique : ignore une annonce dont la carte
        # a changé de mains ou a été recyclée depuis (annonce caduque).
        if not card or card.user_id != target.id:
            continue
        resource = await session.get(Resource, listing.resource_id)
        trade_listings.append(TradeListingOut(
            slot=listing.slot,
            card=await build_card_response(session, card),
            resource_id=listing.resource_id,
            resource_name=resource.name if resource else listing.resource_id,
            price=listing.price,
            mode=listing.mode,
        ))

    return ShowcaseResponse(
        user_id=target.id, username=target.username, display_name=target.display_name,
        avatar=avatar, cards=cards, trade_listings=trade_listings,
    )
