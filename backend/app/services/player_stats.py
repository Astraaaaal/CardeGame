"""
Statistiques enrichies du joueur (onglet Statistiques du profil) — mélange
de stats sérieuses (collection, puissance, social) et plus ludiques (carte
fétiche, plus gros doublon, type favori...), calculées à la demande.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, or_

from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character
from app.models.achievement import AchievementDef, UserAchievement
from app.models.message import Message
from app.models.social import FriendRequest
from app.models.trade_session import TradeSession, STATUS_COMPLETED
from app.services.card_view import build_card_response
from app.services.power import combined_rarity as _combined_rarity
from app.services.levels import get_all_tiers, current_level_for_power
from app.services.wallet import get_balance
from app.services.achievements import sync_unlocked

DUST_ID = "dust"  # seule ressource secondaire pour l'instant (cf. app/api/collection.py::RECYCLE_RESOURCE_ID)


async def build_player_stats(session: AsyncSession, user: User) -> dict:
    cards = (await session.execute(select(UserCard).where(UserCard.user_id == user.id))).scalars().all()

    total_cards = len(cards)
    unique_keys = {(c.character_id, c.rarity_id, c.quality_id, c.specialty_id, c.jewelry_id) for c in cards}
    unique_cards = len(unique_keys)

    powered = [c for c in cards if c.power is not None]
    total_power = sum(c.power for c in powered)
    average_power = round(total_power / len(powered), 1) if powered else 0.0

    highest_power_card = None
    if powered:
        best = max(powered, key=lambda c: c.power)
        highest_power_card = await build_card_response(session, best)

    luckiest_card = None
    best_cr = 0
    for c in powered:
        cr = _combined_rarity(c.power, c.drop_probability, c.rarity_id, c.quality_id, c.specialty_id, c.jewelry_id)
        if cr and cr > best_cr:
            best_cr = cr
            luckiest_card = c
    if luckiest_card:
        luckiest_card = await build_card_response(session, luckiest_card)

    # Doublon le plus fréquent (même combo exacte possédée plusieurs fois).
    dup_groups: dict[tuple, list[UserCard]] = {}
    for c in cards:
        key = (c.character_id, c.rarity_id, c.quality_id, c.specialty_id, c.jewelry_id)
        dup_groups.setdefault(key, []).append(c)
    most_duplicated_card = None
    most_duplicated_count = 0
    if dup_groups:
        biggest = max(dup_groups.values(), key=len)
        if len(biggest) > 1:
            most_duplicated_count = len(biggest)
            most_duplicated_card = await build_card_response(session, biggest[0])

    # Type de personnage le plus représenté (doublons inclus).
    char_ids = {c.character_id for c in cards}
    chars = {}
    if char_ids:
        rows = (await session.execute(select(Character).where(Character.id.in_(char_ids)))).scalars().all()
        chars = {ch.id: ch for ch in rows}
    type_counts: dict[str, int] = {}
    for c in cards:
        char = chars.get(c.character_id)
        if char:
            type_counts[char.type] = type_counts.get(char.type, 0) + 1
    favorite_type_name = None
    favorite_type_count = 0
    if type_counts:
        favorite_type_name, favorite_type_count = max(type_counts.items(), key=lambda kv: kv[1])

    oldest_card = None
    if cards:
        oldest = min(cards, key=lambda c: c.obtained_at)
        oldest_card = await build_card_response(session, oldest)

    tiers = await get_all_tiers(session)
    current_level = current_level_for_power(tiers, total_power)

    # Débloque tout ce qui vient d'être atteint avant de compter — sinon un
    # joueur qui n'a jamais ouvert l'onglet Achievements verrait un compte
    # à zéro ici même en ayant déjà rempli des conditions.
    await sync_unlocked(session, user)

    achievements_total = (await session.execute(
        select(func.count()).select_from(AchievementDef).where(AchievementDef.active == True)  # noqa: E712
    )).scalar() or 0
    achievements_unlocked = (await session.execute(
        select(func.count()).select_from(UserAchievement).where(UserAchievement.user_id == user.id)
    )).scalar() or 0

    friends_count = (await session.execute(
        select(func.count()).select_from(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(FriendRequest.requester_id == user.id, FriendRequest.addressee_id == user.id),
        )
    )).scalar() or 0
    trades_completed = (await session.execute(
        select(func.count()).select_from(TradeSession).where(
            TradeSession.status == STATUS_COMPLETED,
            or_(TradeSession.user_a_id == user.id, TradeSession.user_b_id == user.id),
        )
    )).scalar() or 0
    gifts_sent = (await session.execute(
        select(func.count()).select_from(Message).where(
            Message.sender_type == "player", Message.sender_user_id == user.id,
        )
    )).scalar() or 0
    gifts_received = (await session.execute(
        select(func.count()).select_from(Message).where(
            Message.sender_type == "player", Message.recipient_user_id == user.id,
        )
    )).scalar() or 0

    dust = await get_balance(session, user, DUST_ID)

    return {
        "total_cards": total_cards,
        "unique_cards": unique_cards,
        "packs_opened": user.packs_opened,
        "cards_recycled": user.cards_recycled,
        "coins": user.coins,
        "dust": dust,
        "total_power": total_power,
        "average_power": average_power,
        "highest_power_card": highest_power_card,
        "luckiest_card": luckiest_card,
        "most_duplicated_card": most_duplicated_card,
        "most_duplicated_count": most_duplicated_count,
        "friends_count": int(friends_count),
        "trades_completed": int(trades_completed),
        "gifts_sent": int(gifts_sent),
        "gifts_received": int(gifts_received),
        "current_level": current_level,
        "achievements_unlocked": int(achievements_unlocked),
        "achievements_total": int(achievements_total),
        "login_streak": user.login_streak,
        "favorite_type_name": favorite_type_name,
        "favorite_type_count": favorite_type_count,
        "oldest_card": oldest_card,
    }
