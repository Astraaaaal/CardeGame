"""
Achievements — évaluation à la demande (pas d'événements suivis en temps
réel : chaque métrique est recalculée quand le joueur consulte sa page,
et débloquée dès que le seuil est franchi). Les paramètres et récompenses
vivent dans AchievementDef (éditable depuis l'admin).
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, or_

from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character, CharacterType
from app.models.economy import ShopPurchase
from app.models.quest import UserQuest
from app.models.social import FriendRequest
from app.models.message import Message
from app.models.trade_session import TradeSession, STATUS_COMPLETED
from app.models.achievement import AchievementDef, UserAchievement
from app.services.levels import current_level_for_power, get_all_tiers, get_total_power
from app.services.power import combined_rarity as _combined_rarity
from app.services.wallet import apply_delta
from app.services import booster_inventory


async def _trades_completed(session: AsyncSession, user_id: int) -> int:
    rows = (await session.execute(
        select(func.count()).select_from(TradeSession).where(
            TradeSession.status == STATUS_COMPLETED,
            or_(TradeSession.user_a_id == user_id, TradeSession.user_b_id == user_id),
        )
    )).scalar()
    return int(rows or 0)


async def _friends_count(session: AsyncSession, user_id: int) -> int:
    rows = (await session.execute(
        select(func.count()).select_from(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(FriendRequest.requester_id == user_id, FriendRequest.addressee_id == user_id),
        )
    )).scalar()
    return int(rows or 0)


async def _gifts_sent(session: AsyncSession, user_id: int) -> int:
    rows = (await session.execute(
        select(func.count()).select_from(Message).where(
            Message.sender_type == "player", Message.sender_user_id == user_id,
        )
    )).scalar()
    return int(rows or 0)


async def _types_owned_distinct(session: AsyncSession, user_id: int) -> tuple[int, int]:
    owned = (await session.execute(
        select(Character.type).distinct()
        .join(UserCard, UserCard.character_id == Character.id)
        .where(UserCard.user_id == user_id)
    )).scalars().all()
    total = (await session.execute(select(func.count()).select_from(CharacterType))).scalar()
    return len(owned), int(total or 0)


async def _has_complete_type(session: AsyncSession, user_id: int) -> bool:
    owned_rows = (await session.execute(
        select(Character.type, UserCard.character_id).distinct()
        .join(UserCard, UserCard.character_id == Character.id)
        .where(UserCard.user_id == user_id)
    )).all()
    owned_by_type: dict[str, set] = {}
    for t, cid in owned_rows:
        owned_by_type.setdefault(t, set()).add(cid)

    all_rows = (await session.execute(select(Character.type, Character.id))).all()
    total_by_type: dict[str, set] = {}
    for t, cid in all_rows:
        total_by_type.setdefault(t, set()).add(cid)

    return any(ids and owned_by_type.get(t, set()) >= ids for t, ids in total_by_type.items())


async def _has_card_with(session: AsyncSession, user_id: int, column, value: str) -> bool:
    row = (await session.execute(
        select(UserCard.id).where(UserCard.user_id == user_id, column == value).limit(1)
    )).first()
    return row is not None


async def _max_power(session: AsyncSession, user_id: int) -> int:
    val = (await session.execute(
        select(func.max(UserCard.power)).where(UserCard.user_id == user_id)
    )).scalar()
    return int(val or 0)


async def _max_combined_rarity(session: AsyncSession, user_id: int) -> int:
    rows = (await session.execute(
        select(UserCard.power, UserCard.drop_probability, UserCard.rarity_id,
               UserCard.quality_id, UserCard.specialty_id, UserCard.jewelry_id)
        .where(UserCard.user_id == user_id, UserCard.power != None)  # noqa: E711
    )).all()
    best = 0
    for power, prob, rarity_id, quality_id, specialty_id, jewelry_id in rows:
        cr = _combined_rarity(power, prob, rarity_id, quality_id, specialty_id, jewelry_id)
        if cr and cr > best:
            best = cr
    return best


async def count_shop_purchases(session: AsyncSession, user_id: int) -> int:
    return int((await session.execute(
        select(func.count()).select_from(ShopPurchase).where(ShopPurchase.user_id == user_id)
    )).scalar() or 0)


async def count_quests_completed(session: AsyncSession, user_id: int, period: str | None = None) -> int:
    query = select(func.count()).select_from(UserQuest).where(
        UserQuest.user_id == user_id, UserQuest.claimed_at != None,  # noqa: E711
    )
    if period:
        query = query.where(UserQuest.period == period)
    return int((await session.execute(query)).scalar() or 0)


async def collection_completion(session: AsyncSession, user_id: int) -> tuple[int, int]:
    """(personnages différents possédés, personnages existants)."""
    owned = (await session.execute(
        select(func.count(func.distinct(UserCard.character_id))).where(UserCard.user_id == user_id)
    )).scalar() or 0
    total = (await session.execute(select(func.count()).select_from(Character))).scalar() or 0
    return int(owned), int(total)


async def evaluate_metric(session: AsyncSession, user: User, achievement: AchievementDef) -> int:
    """Retourne la valeur courante de la métrique de cet achievement pour ce joueur
    (comparée à `achievement.threshold` par l'appelant pour savoir si débloqué)."""
    metric = achievement.metric
    if metric == "total_cards":
        return user.total_cards
    if metric == "packs_opened":
        return user.packs_opened
    if metric == "trades_completed":
        return await _trades_completed(session, user.id)
    if metric == "friends_count":
        return await _friends_count(session, user.id)
    if metric == "gifts_sent":
        return await _gifts_sent(session, user.id)
    if metric == "cards_recycled":
        return user.cards_recycled
    if metric == "coins_balance":
        return user.coins
    if metric == "login_streak":
        return user.login_streak
    if metric == "level":
        tiers = await get_all_tiers(session)
        total_power = await get_total_power(session, user.id)
        return current_level_for_power(tiers, total_power)
    if metric == "types_owned_distinct":
        owned, _total = await _types_owned_distinct(session, user.id)
        return owned
    if metric == "type_complete":
        return 1 if await _has_complete_type(session, user.id) else 0
    if metric == "rarity_owned":
        return 1 if await _has_card_with(session, user.id, UserCard.rarity_id, achievement.metric_param) else 0
    if metric == "jewelry_owned":
        return 1 if await _has_card_with(session, user.id, UserCard.jewelry_id, achievement.metric_param) else 0
    if metric == "specialty_owned":
        return 1 if await _has_card_with(session, user.id, UserCard.specialty_id, achievement.metric_param) else 0
    if metric == "card_power":
        return await _max_power(session, user.id)
    if metric == "combined_rarity":
        return await _max_combined_rarity(session, user.id)
    if metric == "shop_purchases":
        return await count_shop_purchases(session, user.id)
    if metric == "rerolls_used":
        return user.rerolls_used
    if metric == "reroll_rarity_upgrades":
        return user.reroll_rarity_upgrades
    if metric == "quests_completed":
        return await count_quests_completed(session, user.id)
    if metric == "best_login_streak":
        return max(user.best_login_streak, user.login_streak)
    if metric == "rank_reached":
        top = int(achievement.metric_param or 0)
        return 1 if user.best_global_rank and top and user.best_global_rank <= top else 0
    if metric == "collection_completion_pct":
        owned, total = await collection_completion(session, user.id)
        return owned * 100 // total if total else 0
    if metric == "rarity_count":
        return int((await session.execute(
            select(func.count()).select_from(UserCard).where(
                UserCard.user_id == user.id, UserCard.rarity_id == achievement.metric_param,
            )
        )).scalar() or 0)
    if metric == "specialty_jewelry_owned":
        specialty_id, _, jewelry_id = (achievement.metric_param or "").partition(":")
        row = (await session.execute(
            select(UserCard.id).where(
                UserCard.user_id == user.id, UserCard.specialty_id == specialty_id, UserCard.jewelry_id == jewelry_id,
            ).limit(1)
        )).first()
        return 1 if row else 0
    if metric == "meta_unlocked_ratio":
        total_defs = (await session.execute(
            select(func.count()).select_from(AchievementDef).where(
                AchievementDef.active == True, AchievementDef.metric != "meta_unlocked_ratio",  # noqa: E712
            )
        )).scalar() or 0
        unlocked = (await session.execute(
            select(func.count()).select_from(UserAchievement).where(UserAchievement.user_id == user.id)
        )).scalar() or 0
        return round(unlocked / total_defs * 100) if total_defs else 0
    return 0


async def effective_threshold(session: AsyncSession, achievement: AchievementDef) -> int:
    """Le seuil réel à afficher/comparer — pour "types_owned_distinct" c'est le
    nombre ACTUEL de types existants (peut grandir avec le contenu du jeu),
    pas la valeur figée en base au moment du seed."""
    if achievement.metric == "types_owned_distinct":
        total = (await session.execute(select(func.count()).select_from(CharacterType))).scalar()
        return int(total or achievement.threshold)
    return achievement.threshold


async def sync_unlocked(session: AsyncSession, user: User) -> list[UserAchievement]:
    """Débloque (crée UserAchievement) tout ce qui vient d'atteindre son seuil.
    Ne touche jamais un achievement déjà débloqué (pas de re-verrouillage)."""
    defs = (await session.execute(
        select(AchievementDef).where(AchievementDef.active == True)  # noqa: E712
    )).scalars().all()
    already = {
        row.achievement_id for row in (await session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        )).scalars().all()
    }

    newly_unlocked = []
    for a in defs:
        if a.id in already:
            continue
        value = await evaluate_metric(session, user, a)
        if value >= await effective_threshold(session, a):
            row = UserAchievement(user_id=user.id, achievement_id=a.id)
            session.add(row)
            newly_unlocked.append(row)

    if newly_unlocked:
        await session.commit()
    return newly_unlocked


async def list_achievements(session: AsyncSession, user: User) -> list[dict]:
    await sync_unlocked(session, user)

    defs = {a.id: a for a in (await session.execute(
        select(AchievementDef).where(AchievementDef.active == True)  # noqa: E712
    )).scalars().all()}
    unlocked = {
        row.achievement_id: row for row in (await session.execute(
            select(UserAchievement).where(UserAchievement.user_id == user.id)
        )).scalars().all()
    }

    out = []
    for a in defs.values():
        ua = unlocked.get(a.id)
        threshold = await effective_threshold(session, a)
        progress = await evaluate_metric(session, user, a) if not ua else threshold
        out.append({
            "id": a.id, "name": a.name, "description": a.description, "category": a.category,
            "threshold": threshold, "progress": min(progress, threshold),
            "reward_resource_id": a.reward_resource_id, "reward_amount": a.reward_amount,
            "reward_booster_id": a.reward_booster_id,
            "unlocked_at": ua.unlocked_at if ua else None,
            "claimed_at": ua.claimed_at if ua else None,
        })

    # Empilage : les achievements incrémentaux (même métrique + même
    # paramètre, ex. total_cards à 10/50/100/250/500) ne montrent que le
    # PROCHAIN palier non encore récupéré — les précédents (récupérés)
    # restent masqués, comme les suivants (pas encore atteints). Si toute
    # la chaîne est récupérée, on garde le dernier palier (état "terminé").
    # Classement (top 10 → top 3 → 1re place) : une seule chaîne, le paramètre
    # étant le palier lui-même (plus il est petit, plus il est difficile).
    def chain_key(a: AchievementDef) -> tuple:
        return (a.metric, None) if a.metric == "rank_reached" else (a.metric, a.metric_param)

    def difficulty(a: AchievementDef) -> int:
        return -int(a.metric_param or 0) if a.metric == "rank_reached" else a.threshold

    chains: dict[tuple, list[AchievementDef]] = {}
    for a in defs.values():
        chains.setdefault(chain_key(a), []).append(a)

    visible_ids = set()
    for members in chains.values():
        if len(members) == 1:
            visible_ids.add(members[0].id)
            continue
        members.sort(key=difficulty)
        chosen = next(
            (a for a in members if not (unlocked.get(a.id) and unlocked[a.id].claimed_at)),
            members[-1],
        )
        visible_ids.add(chosen.id)

    out = [o for o in out if o["id"] in visible_ids]
    out.sort(key=lambda x: (x["category"], x["unlocked_at"] is None, x["name"]))
    return out


async def claim_achievement(session: AsyncSession, user: User, achievement_id: str) -> dict:
    ua = await session.get(UserAchievement, (user.id, achievement_id))
    if not ua:
        raise HTTPException(404, "Achievement pas encore débloqué.")
    if ua.claimed_at:
        raise HTTPException(409, "Récompense déjà récupérée.")

    a = await session.get(AchievementDef, achievement_id)
    if not a:
        raise HTTPException(404, "Achievement introuvable.")

    if a.reward_resource_id and a.reward_amount:
        await apply_delta(session, user, a.reward_resource_id, a.reward_amount)
    if a.reward_booster_id:
        # Crédité à l'inventaire plutôt qu'ouvert directement — le joueur
        # l'ouvre depuis la boutique, avec la même animation qu'un achat.
        await booster_inventory.grant(session, user.id, a.reward_booster_id, 1)

    ua.claimed_at = datetime.utcnow()
    session.add(ua)
    await session.commit()
    await session.refresh(ua)

    # Construit la réponse directement plutôt que de la piocher dans
    # list_achievements() : cet achievement vient d'être récupéré, donc le
    # filtrage "empilage" de list_achievements (qui masque les paliers d'une
    # chaîne déjà récupérés au profit du suivant) l'exclurait désormais de sa
    # sortie, faisant échouer la validation de la réponse (AchievementOut).
    threshold = await effective_threshold(session, a)
    return {
        "id": a.id, "name": a.name, "description": a.description, "category": a.category,
        "threshold": threshold, "progress": threshold,
        "reward_resource_id": a.reward_resource_id, "reward_amount": a.reward_amount,
        "reward_booster_id": a.reward_booster_id,
        "unlocked_at": ua.unlocked_at, "claimed_at": ua.claimed_at,
    }
