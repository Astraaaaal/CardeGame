"""
Construction d'un ShowcaseResponse à partir d'un User — factorisé pour être
réutilisé par la route publique (voir un joueur) et la route d'édition (moi).
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_

from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import Resource
from app.models.social import TradeListing, FriendRequest
from app.models.achievement import AchievementDef, UserAchievement
from app.schemas.showcase import ShowcaseResponse, AvatarInfo, TradeListingOut, ShowcaseAchievement
from app.services.card_view import build_card_response
from app.services.levels import get_all_tiers, get_total_power, current_level_for_power
from app.services.ranking import current_global_rank

ACHIEVEMENT_SLOT_FIELDS = ("showcase_achievement_1_id", "showcase_achievement_2_id", "showcase_achievement_3_id")


async def build_showcase_response(session: AsyncSession, target: User, viewer_id: int | None = None) -> ShowcaseResponse:
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

    achievement_slots = [getattr(target, f) for f in ACHIEVEMENT_SLOT_FIELDS]
    achievements = []
    for achievement_id in achievement_slots:
        if not achievement_id:
            continue
        definition = await session.get(AchievementDef, achievement_id)
        if definition and await session.get(UserAchievement, (target.id, achievement_id)):
            achievements.append(ShowcaseAchievement(
                id=definition.id, name=definition.name,
                description=definition.description, category=definition.category,
            ))

    level = current_level_for_power(await get_all_tiers(session), await get_total_power(session, target.id))

    friendship_status = "self"
    if viewer_id is not None and viewer_id != target.id:
        rel = (await session.execute(
            select(FriendRequest).where(
                or_(
                    and_(FriendRequest.requester_id == viewer_id, FriendRequest.addressee_id == target.id),
                    and_(FriendRequest.requester_id == target.id, FriendRequest.addressee_id == viewer_id),
                )
            )
        )).scalar_one_or_none()
        if rel and rel.status == "accepted":
            friendship_status = "friends"
        elif rel and rel.status == "pending":
            friendship_status = "pending"
        else:
            friendship_status = "none"

    return ShowcaseResponse(
        user_id=target.id, username=target.username, display_name=target.display_name,
        avatar=avatar, cards=cards, trade_listings=trade_listings,
        friendship_status=friendship_status,
        level=level,
        best_login_streak=max(target.best_login_streak, target.login_streak),
        current_global_rank=await current_global_rank(session, target.id),
        best_global_rank=target.best_global_rank,
        achievements=achievements,
        achievement_slots=achievement_slots,
    )
