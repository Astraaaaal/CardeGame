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
from app.services import guilds, level_gap, monthly, trade_tax
from app.services.card_view import build_card_response
from app.services.levels import get_all_tiers, get_total_power, current_level_for_power
from app.services.ranking import current_global_rank
from app.models.premium import Cosmetic, UserCosmetic
from app.schemas.premium import CosmeticOut

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
    viewer = await session.get(User, viewer_id) if viewer_id and viewer_id != target.id else None
    viewer_rate = await trade_tax.rate_for(session, viewer, target) if viewer else 0
    gap, gap_limit = await level_gap.between(session, viewer, target) if viewer else (0, 0)
    gap_reason = level_gap.reason(gap, gap_limit) if viewer and gap > gap_limit else None
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
            tax=await trade_tax.tax_for_items(session, viewer_rate, [{"type": "card", "card": card}]) if viewer_rate else 0,
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

    total_power = await get_total_power(session, target.id)
    level = current_level_for_power(await get_all_tiers(session), total_power)

    async def equipped(cosmetic_id: str | None) -> CosmeticOut | None:
        # Re-vérifie la possession : un cosmétique retiré ne s'affiche plus.
        if not cosmetic_id or not await session.get(UserCosmetic, (target.id, cosmetic_id)):
            return None
        c = await session.get(Cosmetic, cosmetic_id)
        return CosmeticOut(
            id=c.id, kind=c.kind, name=c.name, description=c.description, color_from=c.color_from,
            color_to=c.color_to, animation=c.animation, image_url=c.image_url, active=c.active,
        ) if c else None

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
        total_power=total_power,
        best_login_streak=max(target.best_login_streak, target.login_streak),
        current_global_rank=await current_global_rank(session, target.id),
        best_global_rank=target.best_global_rank,
        monthly_badge=await monthly.champion_badge(session, target.id),
        trade_gap_reason=gap_reason,
        achievements=achievements,
        achievement_slots=achievement_slots,
        avatar_frame=await equipped(target.equipped_avatar_frame_id),
        showcase_background=await equipped(target.equipped_showcase_background_id),
        guild=(await guilds.tags_for(session, [target.id])).get(target.id),
    )
