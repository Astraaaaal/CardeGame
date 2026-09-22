"""
Remise à zéro de tous les comptes (fin de bêta) : chaque joueur garde son
compte (pseudo, e-mail, mot de passe), ses réglages, ses amis et ses groupes
d'amis ; tout le reste repart comme un compte neuf. Tout le monde est déconnecté.
"""

from sqlalchemy import delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.achievement import UserAchievement
from app.models.activity import Expedition, HigherLowerGame, UserActivity
from app.models.booster_inventory import UserBonusBooster, UserBoosterInventory
from app.models.card import UserCard
from app.models.economy import Resource, ShopPurchase, UserResource
from app.models.favorite import FavoriteCard, FavoriteCategory
from app.models.guild import (
    Guild, GuildBuff, GuildContribution, GuildInvite, GuildMember, GuildMessage, GuildWeek,
)
from app.models.message import Message
from app.models.monthly import GuildMonthlyScore, MonthlyResult, MonthlyScore
from app.models.premium import PremiumOrder, UserCosmetic
from app.models.quest import QuestProgress, UserQuest
from app.models.reroll_inventory import UserRerollToken
from app.models.social import FriendRequest, TradeListing, TradeRequest
from app.models.token import RefreshToken
from app.models.trade_session import TradeSession, TradeSessionItem
from app.models.user import User
from app.services.wallet import COINS_ID

# Tables vidées entièrement, dans un ordre compatible avec les clés étrangères.
_WIPED = (
    FavoriteCard, FavoriteCategory,
    TradeSessionItem, TradeSession, TradeRequest, TradeListing, Message,
    GuildContribution, GuildBuff, GuildMessage, GuildWeek, GuildInvite, GuildMember, Guild,
    UserAchievement, QuestProgress, UserQuest,
    UserActivity, Expedition, HigherLowerGame,
    UserBoosterInventory, UserBonusBooster, UserRerollToken, UserCosmetic,
    ShopPurchase, UserResource, RefreshToken,
    MonthlyScore, GuildMonthlyScore, MonthlyResult,
)


async def reset_all_accounts(session: AsyncSession) -> dict:
    """Ne touche qu'aux données de jeu ; commit à la fin (tout ou rien)."""
    users = (await session.execute(select(func.count()).select_from(User))).scalar_one()
    cards = (await session.execute(select(func.count()).select_from(UserCard))).scalar_one()

    for model in _WIPED:
        await session.execute(delete(model))
    # Demandes d'ami en attente supprimées ; les amitiés (acceptées) restent.
    await session.execute(delete(FriendRequest).where(FriendRequest.status != "accepted"))
    # Commandes en euros conservées pour la comptabilité, détachées des comptes
    # (sinon elles compteraient encore dans les limites d'achat).
    await session.execute(update(PremiumOrder).values(user_id=None))

    resources = (await session.execute(select(Resource))).scalars().all()
    coins_start = next((r.starting_amount for r in resources if r.id == COINS_ID), 500)
    await session.execute(update(User).values(
        coins=coins_start, packs_opened=0, total_cards=0,
        login_streak=0, best_login_streak=0, last_daily_claim=None, best_global_rank=None,
        avatar_character_id=None,
        showcase_card_1_id=None, showcase_card_2_id=None, showcase_card_3_id=None,
        showcase_achievement_1_id=None, showcase_achievement_2_id=None, showcase_achievement_3_id=None,
        equipped_avatar_frame_id=None, equipped_showcase_background_id=None,
        cards_recycled=0, dust_from_recycling=0, rerolls_used=0, reroll_rarity_upgrades=0,
        best_reroll_card_id=None, best_reroll_combined_rarity=None, login_days_total=0,
        guild_left_at=None, claimed_level=0, max_level=1,
    ))
    await session.execute(delete(UserCard))

    user_ids = (await session.execute(select(User.id))).scalars().all()
    for r in resources:
        if r.id != COINS_ID and r.starting_amount > 0:
            session.add_all(UserResource(user_id=uid, resource_id=r.id, amount=r.starting_amount) for uid in user_ids)

    await session.commit()
    return {"users": users, "cards_removed": cards}
