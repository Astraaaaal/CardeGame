"""
Suppression de compte — self-service, définitive et irréversible. Supprime
toute trace du joueur (cartes, ressources, messages, échanges, amis, etc.)
dans l'ordre compatible avec les contraintes de clé étrangère.
"""

from sqlalchemy import delete, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.card import UserCard
from app.models.economy import UserResource, ShopPurchase
from app.models.social import FriendRequest, TradeRequest, TradeListing, CloseFriend, FriendGroup, FriendGroupMember
from app.models.token import RefreshToken
from app.models.message import Message
from app.models.achievement import UserAchievement
from app.models.quest import QuestProgress, UserQuest
from app.models.booster_inventory import UserBoosterInventory, UserBonusBooster
from app.models.reroll_inventory import UserRerollToken
from app.models.premium import UserCosmetic, PremiumOrder
from app.services import account_email
from app.models.trade_session import TradeSession, TradeSessionItem


async def delete_account(session: AsyncSession, user: User) -> None:
    user_id = user.id

    sess_ids = [s.id for s in (await session.execute(
        select(TradeSession).where(or_(TradeSession.user_a_id == user_id, TradeSession.user_b_id == user_id))
    )).scalars().all()]
    if sess_ids:
        await session.execute(delete(TradeSessionItem).where(TradeSessionItem.session_id.in_(sess_ids)))
        await session.execute(delete(TradeSession).where(TradeSession.id.in_(sess_ids)))

    await session.execute(delete(UserBoosterInventory).where(UserBoosterInventory.user_id == user_id))
    await session.execute(delete(UserBonusBooster).where(UserBonusBooster.user_id == user_id))
    await session.execute(delete(UserRerollToken).where(UserRerollToken.user_id == user_id))
    await session.execute(delete(UserCosmetic).where(UserCosmetic.user_id == user_id))
    # Commandes conservées pour la comptabilité, détachées du compte.
    await session.execute(update(PremiumOrder).where(PremiumOrder.user_id == user_id).values(user_id=None))
    await account_email.purge_for_user(session, user)
    await session.execute(delete(UserAchievement).where(UserAchievement.user_id == user_id))
    await session.execute(delete(QuestProgress).where(QuestProgress.user_id == user_id))
    await session.execute(delete(UserQuest).where(UserQuest.user_id == user_id))
    await session.execute(delete(Message).where(
        or_(Message.sender_user_id == user_id, Message.recipient_user_id == user_id)
    ))
    await session.execute(update(User).where(User.id == user_id).values(
        avatar_character_id=None, showcase_card_1_id=None, showcase_card_2_id=None, showcase_card_3_id=None))
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await session.execute(delete(TradeListing).where(TradeListing.user_id == user_id))
    await session.execute(delete(UserCard).where(UserCard.user_id == user_id))
    await session.execute(delete(UserResource).where(UserResource.user_id == user_id))
    await session.execute(delete(ShopPurchase).where(ShopPurchase.user_id == user_id))
    await session.execute(delete(FriendRequest).where(
        or_(FriendRequest.requester_id == user_id, FriendRequest.addressee_id == user_id)
    ))
    await session.execute(delete(TradeRequest).where(
        or_(TradeRequest.requester_id == user_id, TradeRequest.addressee_id == user_id)
    ))
    await session.execute(delete(CloseFriend).where(
        or_(CloseFriend.user_id == user_id, CloseFriend.friend_user_id == user_id)
    ))
    # Appartenance de ce user dans les groupes d'AUTRUI (ses propres groupes
    # sont supprimés juste après, ce qui vide leurs membres via ON DELETE CASCADE).
    await session.execute(delete(FriendGroupMember).where(FriendGroupMember.friend_user_id == user_id))
    await session.execute(delete(FriendGroup).where(FriendGroup.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
    await session.commit()
