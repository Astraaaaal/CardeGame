"""
Statistiques enrichies du joueur (onglet Statistiques du profil) — mélange
de stats sérieuses (collection, puissance, social) et plus ludiques (carte
fétiche, plus gros doublon, type favori...), calculées à la demande.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case
from sqlmodel import select, func, or_

from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character
from app.models.achievement import AchievementDef, UserAchievement
from app.models.activity import HigherLowerGame
from app.models.message import Message
from app.models.social import FriendRequest
from app.models.trade_session import TradeSession, STATUS_COMPLETED
from app.services.card_view import build_card_response
from app.services.power import combined_rarity as _combined_rarity
from app.services.levels import get_all_tiers, current_level_for_power, get_total_power
from app.services.wallet import get_balance
from app.services.achievements import (
    sync_unlocked, count_shop_purchases, count_quests_completed, collection_completion,
)
from app.services.ranking import current_global_rank
from app.models.reference import Rarity, Specialty, Jewelry

DUST_ID = "dust"  # seule ressource secondaire pour l'instant (cf. app/api/collection.py::RECYCLE_RESOURCE_ID)


async def higher_lower_record(session: AsyncSession, user_id: int) -> dict:
    """Bilan du « plus ou moins », lu sur les parties elles-mêmes : rien n'est
    compté à part, donc rien ne peut diverger. Une remise à zéro vide la table
    et le bilan repart avec la saison.

    Le solde est donné PAR RESSOURCE : additionner des pièces et de la poussière
    ne voudrait rien dire. Les pièces passent devant, c'est la mise courante."""
    rows = (await session.execute(
        select(
            HigherLowerGame.resource_id,
            func.count().label("parties"),
            func.sum(HigherLowerGame.stake).label("mise"),
            func.sum(HigherLowerGame.payout).label("gain"),
            func.sum(case((HigherLowerGame.status == "cashed", 1), else_=0)).label("encaissees"),
        )
        .where(HigherLowerGame.user_id == user_id, HigherLowerGame.status != "active")
        .group_by(HigherLowerGame.resource_id)
    )).all()
    par_ressource = [
        {
            "resource_id": r.resource_id,
            "games": int(r.parties or 0),
            "won_games": int(r.encaissees or 0),
            "wagered": int(r.mise or 0),
            "returned": int(r.gain or 0),
            "net": int(r.gain or 0) - int(r.mise or 0),
        }
        for r in rows
    ]
    par_ressource.sort(key=lambda d: (d["resource_id"] != "coins", -d["games"]))
    return {
        "games": sum(d["games"] for d in par_ressource),
        "won_games": sum(d["won_games"] for d in par_ressource),
        "by_resource": par_ressource,
    }


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
        cr = _combined_rarity(c.power, c.drop_probability, c.rarity_id, c.quality_id,
                              c.specialty_id, c.jewelry_id, c.power_probability)
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
    # Le niveau se calcule sur les contributions PLAFONNÉES, pas sur la
    # puissance brute affichée juste au-dessus (cf. LEVEL_CONTRIBUTION_CAP).
    # Les deux sommes diffèrent dès qu'on possède des cartes puissantes : cette
    # fiche annonçait donc un niveau plus élevé que celui dont dépendent les
    # déblocages, le classement et la vitrine.
    current_level = current_level_for_power(tiers, await get_total_power(session, user.id))

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

    # Collection détaillée : complétion et répartition par rareté / spécialité / bijou.
    characters_owned, characters_total = await collection_completion(session, user.id)

    async def breakdown(model, attr: str, skip: set[str]) -> list[dict]:
        refs = (await session.execute(select(model))).scalars().all()
        counts: dict[str, int] = {}
        for c in cards:
            counts[getattr(c, attr)] = counts.get(getattr(c, attr), 0) + 1
        return [
            {"id": r.id, "name": r.name, "count": counts.get(r.id, 0)}
            for r in sorted(refs, key=lambda r: -r.weight) if r.id not in skip
        ]

    best_reroll_card = None
    if user.best_reroll_card_id:
        card = await session.get(UserCard, user.best_reroll_card_id)
        if card and card.user_id == user.id:
            best_reroll_card = await build_card_response(session, card)

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
        "characters_owned": characters_owned,
        "characters_total": characters_total,
        "rarity_counts": await breakdown(Rarity, "rarity_id", set()),
        "specialty_counts": await breakdown(Specialty, "specialty_id", {"normal"}),
        "jewelry_counts": await breakdown(Jewelry, "jewelry_id", {"none"}),
        "shop_purchases": await count_shop_purchases(session, user.id),
        "rerolls_used": user.rerolls_used,
        "dust_from_recycling": user.dust_from_recycling,
        "best_reroll_card": best_reroll_card,
        "current_global_rank": await current_global_rank(session, user.id),
        "best_global_rank": user.best_global_rank,
        "best_login_streak": max(user.best_login_streak, user.login_streak),
        "login_days_total": user.login_days_total,
        "higher_lower": await higher_lower_record(session, user.id),
        "daily_quests_completed": await count_quests_completed(session, user.id, "daily"),
        "weekly_quests_completed": await count_quests_completed(session, user.id, "weekly"),
    }
