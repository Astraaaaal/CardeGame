"""
Logique de la session d'échange en direct — création, ajout/retrait
d'objets, double "prêt" + double "confirmer", exécution atomique.
"""

from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_

from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import Resource
from app.models.booster import Booster
from app.models.booster_inventory import UserBonusBooster, UserBoosterInventory
from app.models.reroll_inventory import UserRerollToken
from app.models.trade_session import (
    TradeSession, TradeSessionItem,
    STATUS_NEGOTIATING, STATUS_CONFIRMING, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_EXPIRED,
    ACTIVE_STATUSES, MAX_ITEMS_PER_SIDE, EXPIRE_AFTER_MINUTES, ABSENT_EXPIRE_MINUTES,
)
from app.schemas.trade_session import TradeSessionOut, TradeSessionItemOut
from app.services.card_view import build_card_response
from app.services.wallet import get_balance, apply_delta, COINS_ID
from app.services import booster_inventory, quest_progress, reroll_inventory
from app.services.presence import is_online as _is_online
from app.services.premium import ensure_tradeable


_AXIS_LABEL = {"rarity": "rareté", "quality": "qualité", "specialty": "spécialité", "jewelry": "bijou"}


def _side(trade: TradeSession, user_id: int) -> str:
    if user_id == trade.user_a_id:
        return "a"
    if user_id == trade.user_b_id:
        return "b"
    raise HTTPException(403, "Tu ne fais pas partie de cet échange.")


def _other_id(trade: TradeSession, user_id: int) -> int:
    return trade.user_b_id if user_id == trade.user_a_id else trade.user_a_id


async def get_active_session_for(session: AsyncSession, user_id: int) -> TradeSession | None:
    row = (await session.execute(
        select(TradeSession).where(
            TradeSession.status.in_(ACTIVE_STATUSES),
            or_(TradeSession.user_a_id == user_id, TradeSession.user_b_id == user_id),
        )
    )).scalar_one_or_none()
    if row:
        await maybe_expire(session, row)
        if row.status in ACTIVE_STATUSES:
            return row
        return None
    return None


async def create_session(session: AsyncSession, user_a_id: int, user_b_id: int) -> TradeSession:
    # Verrouille les deux joueurs (ordre fixe, anti-deadlock) : deux demandes
    # du même joueur acceptées au même instant ne doivent ouvrir qu'une session.
    await session.execute(
        select(User.id).where(User.id.in_([user_a_id, user_b_id])).order_by(User.id).with_for_update()
    )
    if await get_active_session_for(session, user_a_id):
        raise HTTPException(409, "Tu as déjà un échange en cours.")
    if await get_active_session_for(session, user_b_id):
        raise HTTPException(409, "L'autre joueur a déjà un échange en cours.")
    trade = TradeSession(user_a_id=user_a_id, user_b_id=user_b_id)
    session.add(trade)
    await session.commit()
    await session.refresh(trade)
    return trade


async def get_session_or_404(session: AsyncSession, session_id: int, user_id: int) -> TradeSession:
    trade = await session.get(TradeSession, session_id)
    if not trade:
        raise HTTPException(404, "Échange introuvable.")
    _side(trade, user_id)  # lève 403 si l'utilisateur n'en fait pas partie
    await maybe_expire(session, trade)
    await _purge_orphaned_items(session, trade)
    return trade


async def _purge_orphaned_items(session: AsyncSession, trade: TradeSession) -> None:
    """Un item "carte" peut devenir orphelin (user_card_id NULL) si la carte a
    été supprimée par un autre biais (recyclage) pendant que l'échange était en
    cours — cf. ON DELETE SET NULL sur la FK. On le purge dès qu'on le
    détecte, et on redemande "prêt" aux deux joueurs puisque l'offre a changé."""
    if trade.status not in ACTIVE_STATUSES:
        return
    orphans = (await session.execute(
        select(TradeSessionItem).where(
            TradeSessionItem.session_id == trade.id,
            TradeSessionItem.item_type == "card",
            TradeSessionItem.user_card_id.is_(None),
        )
    )).scalars().all()
    if not orphans:
        return
    for item in orphans:
        await session.delete(item)
    trade.status = STATUS_NEGOTIATING
    _reset_ready(trade)
    _touch(trade)
    session.add(trade)
    await session.commit()


async def maybe_expire(session: AsyncSession, trade: TradeSession) -> bool:
    if trade.status not in ACTIVE_STATUSES:
        return False
    now = datetime.utcnow()
    idle = now - trade.updated_at > timedelta(minutes=EXPIRE_AFTER_MINUTES)
    # On ne peut plus quitter un échange : si l'un des deux joueurs a disparu
    # (appli fermée), l'échange expire vite pour ne pas bloquer l'autre.
    absent = False
    for user_id in (trade.user_a_id, trade.user_b_id):
        player = await session.get(User, user_id)
        seen = max(filter(None, [player.last_seen if player else None, trade.created_at]))
        if now - seen > timedelta(minutes=ABSENT_EXPIRE_MINUTES):
            absent = True
    if idle or absent:
        trade.status = STATUS_EXPIRED
        session.add(trade)
        await session.commit()
        return True
    return False


def _touch(trade: TradeSession) -> None:
    trade.updated_at = datetime.utcnow()


def _reset_ready(trade: TradeSession) -> None:
    trade.ready_a = False
    trade.ready_b = False
    trade.confirmed_a = False
    trade.confirmed_b = False


async def _require_negotiating(trade: TradeSession) -> None:
    if trade.status != STATUS_NEGOTIATING:
        raise HTTPException(409, "L'échange n'est plus en négociation — reviens en arrière pour modifier ton offre.")


async def add_card_item(session: AsyncSession, trade: TradeSession, owner_id: int, user_card_id: str) -> TradeSessionItem:
    await _require_negotiating(trade)
    _side(trade, owner_id)

    count = len((await session.execute(
        select(TradeSessionItem).where(TradeSessionItem.session_id == trade.id, TradeSessionItem.owner_id == owner_id)
    )).scalars().all())
    if count >= MAX_ITEMS_PER_SIDE:
        raise HTTPException(400, f"Maximum {MAX_ITEMS_PER_SIDE} objets par échange.")

    card = await session.get(UserCard, user_card_id)
    if not card or card.user_id != owner_id:
        raise HTTPException(404, "Tu ne possèdes pas cette carte.")

    already = (await session.execute(
        select(TradeSessionItem).where(
            TradeSessionItem.session_id == trade.id, TradeSessionItem.user_card_id == user_card_id,
        )
    )).scalar_one_or_none()
    if already:
        raise HTTPException(409, "Cette carte est déjà dans l'échange.")

    item = TradeSessionItem(session_id=trade.id, owner_id=owner_id, item_type="card", user_card_id=user_card_id)
    session.add(item)
    _reset_ready(trade)
    _touch(trade)
    session.add(trade)
    await session.commit()
    await session.refresh(item)
    return item


async def add_resource_item(
    session: AsyncSession, trade: TradeSession, owner_id: int, resource_id: str, amount: int,
) -> TradeSessionItem:
    await _require_negotiating(trade)
    _side(trade, owner_id)

    if amount <= 0:
        raise HTTPException(400, "La quantité doit être positive.")
    await ensure_tradeable(session, resource_id)

    owner = await session.get(User, owner_id)
    balance = await get_balance(session, owner, resource_id)
    if amount > balance:
        raise HTTPException(400, f"Solde insuffisant ({balance}).")

    if resource_id != COINS_ID:
        resource = await session.get(Resource, resource_id)
        if not resource:
            raise HTTPException(404, "Ressource introuvable.")

    existing = (await session.execute(
        select(TradeSessionItem).where(
            TradeSessionItem.session_id == trade.id, TradeSessionItem.owner_id == owner_id,
            TradeSessionItem.item_type == "resource", TradeSessionItem.resource_id == resource_id,
        )
    )).scalar_one_or_none()

    if existing:
        existing.amount = amount
        session.add(existing)
        item = existing
    else:
        count = len((await session.execute(
            select(TradeSessionItem).where(TradeSessionItem.session_id == trade.id, TradeSessionItem.owner_id == owner_id)
        )).scalars().all())
        if count >= MAX_ITEMS_PER_SIDE:
            raise HTTPException(400, f"Maximum {MAX_ITEMS_PER_SIDE} objets par échange.")
        item = TradeSessionItem(session_id=trade.id, owner_id=owner_id, item_type="resource", resource_id=resource_id, amount=amount)
        session.add(item)

    _reset_ready(trade)
    _touch(trade)
    session.add(trade)
    await session.commit()
    await session.refresh(item)
    return item


async def _owned_booster_quantity(
    session: AsyncSession, owner_id: int, booster_id: str, bonus_id: int | None,
) -> int:
    if bonus_id is not None:
        row = await session.get(UserBonusBooster, bonus_id)
        ok = row and row.user_id == owner_id and row.booster_id == booster_id
        return row.quantity if ok else 0
    row = await session.get(UserBoosterInventory, (owner_id, booster_id))
    return row.quantity if row else 0


async def _count_items(session: AsyncSession, trade: TradeSession, owner_id: int) -> int:
    return len((await session.execute(
        select(TradeSessionItem).where(
            TradeSessionItem.session_id == trade.id, TradeSessionItem.owner_id == owner_id,
        )
    )).scalars().all())


async def add_booster_item(
    session: AsyncSession, trade: TradeSession, owner_id: int,
    booster_id: str, bonus_id: int | None, amount: int,
) -> TradeSessionItem:
    """Des boosters non ouverts, avec leur bonus s'ils en ont un."""
    await _require_negotiating(trade)
    _side(trade, owner_id)
    if amount <= 0:
        raise HTTPException(400, "La quantité doit être positive.")
    if not await session.get(Booster, booster_id):
        raise HTTPException(404, "Booster introuvable.")
    owned = await _owned_booster_quantity(session, owner_id, booster_id, bonus_id)
    if amount > owned:
        raise HTTPException(400, f"Tu ne possèdes que {owned} exemplaire(s) de ce booster.")

    existing = (await session.execute(
        select(TradeSessionItem).where(
            TradeSessionItem.session_id == trade.id, TradeSessionItem.owner_id == owner_id,
            TradeSessionItem.item_type == "booster", TradeSessionItem.booster_id == booster_id,
            TradeSessionItem.bonus_id.is_(None) if bonus_id is None else TradeSessionItem.bonus_id == bonus_id,
        )
    )).scalar_one_or_none()
    if existing:
        existing.amount = amount
        item = existing
    else:
        if await _count_items(session, trade, owner_id) >= MAX_ITEMS_PER_SIDE:
            raise HTTPException(400, f"Maximum {MAX_ITEMS_PER_SIDE} objets par échange.")
        item = TradeSessionItem(
            session_id=trade.id, owner_id=owner_id, item_type="booster",
            booster_id=booster_id, bonus_id=bonus_id, amount=amount,
        )
    session.add(item)
    _reset_ready(trade)
    _touch(trade)
    session.add(trade)
    await session.commit()
    await session.refresh(item)
    return item


async def add_reroll_item(
    session: AsyncSession, trade: TradeSession, owner_id: int, token_id: int, amount: int,
) -> TradeSessionItem:
    """Des rerolls de l'inventaire, avec les règles figées à leur achat."""
    await _require_negotiating(trade)
    _side(trade, owner_id)
    if amount <= 0:
        raise HTTPException(400, "La quantité doit être positive.")
    token = await session.get(UserRerollToken, token_id)
    if not token or token.user_id != owner_id:
        raise HTTPException(404, "Reroll introuvable.")
    if amount > token.quantity:
        raise HTTPException(400, f"Tu ne possèdes que {token.quantity} exemplaire(s) de ce reroll.")

    existing = (await session.execute(
        select(TradeSessionItem).where(
            TradeSessionItem.session_id == trade.id, TradeSessionItem.owner_id == owner_id,
            TradeSessionItem.item_type == "reroll", TradeSessionItem.reroll_token_id == token_id,
        )
    )).scalar_one_or_none()
    if existing:
        existing.amount = amount
        item = existing
    else:
        if await _count_items(session, trade, owner_id) >= MAX_ITEMS_PER_SIDE:
            raise HTTPException(400, f"Maximum {MAX_ITEMS_PER_SIDE} objets par échange.")
        item = TradeSessionItem(
            session_id=trade.id, owner_id=owner_id, item_type="reroll",
            reroll_token_id=token_id, amount=amount,
        )
    session.add(item)
    _reset_ready(trade)
    _touch(trade)
    session.add(trade)
    await session.commit()
    await session.refresh(item)
    return item


async def remove_item(session: AsyncSession, trade: TradeSession, owner_id: int, item_id: int) -> None:
    await _require_negotiating(trade)
    item = await session.get(TradeSessionItem, item_id)
    if not item or item.session_id != trade.id or item.owner_id != owner_id:
        raise HTTPException(404, "Objet introuvable dans cet échange.")
    await session.delete(item)
    _reset_ready(trade)
    _touch(trade)
    session.add(trade)
    await session.commit()


async def set_ready(session: AsyncSession, trade: TradeSession, user_id: int, ready: bool) -> TradeSession:
    side = _side(trade, user_id)

    if not ready:
        # Repasse en négociation si on était en confirmation, pour pouvoir remodifier son offre.
        trade.status = STATUS_NEGOTIATING
        _reset_ready(trade)
        _touch(trade)
        session.add(trade)
        await session.commit()
        await session.refresh(trade)
        return trade

    await _require_negotiating(trade)
    if side == "a":
        trade.ready_a = True
    else:
        trade.ready_b = True
    if trade.ready_a and trade.ready_b:
        trade.status = STATUS_CONFIRMING
    _touch(trade)
    session.add(trade)
    await session.commit()
    await session.refresh(trade)
    return trade


async def cancel(session: AsyncSession, trade: TradeSession, user_id: int) -> None:
    _side(trade, user_id)
    if trade.status not in ACTIVE_STATUSES:
        raise HTTPException(409, "Cet échange est déjà terminé.")
    trade.status = STATUS_CANCELLED
    _touch(trade)
    session.add(trade)
    await session.commit()


async def confirm(session: AsyncSession, trade: TradeSession, user_id: int) -> list[str]:
    """Confirme côté `user_id`. Si les deux ont confirmé, exécute l'échange.
    Retourne la liste des messages d'objets invalidés (vide si tout s'est bien passé)."""
    side = _side(trade, user_id)
    if trade.status != STATUS_CONFIRMING:
        raise HTTPException(409, "Les deux joueurs doivent d'abord être prêts.")

    if side == "a":
        trade.confirmed_a = True
    else:
        trade.confirmed_b = True
    _touch(trade)
    session.add(trade)
    await session.commit()
    await session.refresh(trade)

    if trade.confirmed_a and trade.confirmed_b:
        return await _execute_trade(session, trade)
    return []


async def _execute_trade(session: AsyncSession, trade: TradeSession) -> list[str]:
    items = (await session.execute(
        select(TradeSessionItem).where(TradeSessionItem.session_id == trade.id)
    )).scalars().all()

    invalid_items: list[TradeSessionItem] = []
    removed_messages: list[str] = []

    for item in items:
        if item.item_type == "card":
            locked = (await session.execute(
                select(UserCard).where(UserCard.id == item.user_card_id).with_for_update()
            )).scalar_one_or_none()
            if not locked or locked.user_id != item.owner_id:
                name = "Une carte"
                if locked:
                    char = await session.get(Character, locked.character_id)
                    if char:
                        name = char.name
                removed_messages.append(f"{name} n'est plus disponible et a été retirée de l'échange.")
                invalid_items.append(item)
        elif item.item_type == "booster":
            owned = await _owned_booster_quantity(session, item.owner_id, item.booster_id, item.bonus_id)
            if owned < (item.amount or 0):
                removed_messages.append("Boosters plus disponibles — retirés de l'échange.")
                invalid_items.append(item)
        elif item.item_type == "reroll":
            token = await session.get(UserRerollToken, item.reroll_token_id)
            if not token or token.user_id != item.owner_id or token.quantity < (item.amount or 0):
                removed_messages.append("Rerolls plus disponibles — retirés de l'échange.")
                invalid_items.append(item)
        else:
            owner = await session.get(User, item.owner_id)
            balance = await get_balance(session, owner, item.resource_id)
            if balance < (item.amount or 0):
                resource_name = "pièces" if item.resource_id == COINS_ID else (
                    (await session.get(Resource, item.resource_id)).name
                )
                removed_messages.append(f"Solde en {resource_name} insuffisant — retiré de l'échange.")
                invalid_items.append(item)

    if invalid_items:
        for item in invalid_items:
            await session.delete(item)
        trade.status = STATUS_NEGOTIATING
        _reset_ready(trade)
        _touch(trade)
        session.add(trade)
        await session.commit()
        return removed_messages

    user_a = await session.get(User, trade.user_a_id)
    user_b = await session.get(User, trade.user_b_id)

    cards_from_a = cards_from_b = 0
    for item in items:
        other_id = _other_id(trade, item.owner_id)
        if item.item_type == "card":
            card = await session.get(UserCard, item.user_card_id)
            card.user_id = other_id
            session.add(card)
            if item.owner_id == trade.user_a_id:
                cards_from_a += 1
            else:
                cards_from_b += 1
        elif item.item_type == "booster":
            if item.bonus_id is not None:
                row = await booster_inventory.consume_bonus(session, item.owner_id, item.bonus_id, item.amount)
                await booster_inventory.grant_bonus(
                    session, other_id, item.booster_id, row.force_min_rarity_id,
                    row.rarity_weight_multiplier, row.label or "", item.amount,
                )
            else:
                await booster_inventory.consume(session, item.owner_id, item.booster_id, item.amount)
                await booster_inventory.grant(session, other_id, item.booster_id, item.amount)
        elif item.item_type == "reroll":
            token = await reroll_inventory.consume(session, item.owner_id, item.reroll_token_id, item.amount)
            await reroll_inventory.grant_rules(
                session, other_id, token.offer_id, token.label,
                reroll_inventory.rules_of(token), item.amount,
            )
        else:
            owner = user_a if item.owner_id == trade.user_a_id else user_b
            receiver = user_b if item.owner_id == trade.user_a_id else user_a
            await apply_delta(session, owner, item.resource_id, -item.amount)
            await apply_delta(session, receiver, item.resource_id, item.amount)

    user_a.total_cards = max(0, user_a.total_cards - cards_from_a + cards_from_b)
    user_b.total_cards = max(0, user_b.total_cards - cards_from_b + cards_from_a)
    session.add(user_a)
    session.add(user_b)

    await quest_progress.increment(session, trade.user_a_id, "trades_completed", 1)
    await quest_progress.increment(session, trade.user_b_id, "trades_completed", 1)

    trade.status = STATUS_COMPLETED
    _touch(trade)
    session.add(trade)
    await session.commit()
    return []


async def build_out(session: AsyncSession, trade: TradeSession, viewer_id: int, removed_items: list[str] | None = None) -> TradeSessionOut:
    side = _side(trade, viewer_id)
    other_id = _other_id(trade, viewer_id)
    other = await session.get(User, other_id)

    items = (await session.execute(
        select(TradeSessionItem).where(TradeSessionItem.session_id == trade.id)
    )).scalars().all()

    async def _out(item: TradeSessionItem) -> TradeSessionItemOut:
        if item.item_type == "card":
            card = await session.get(UserCard, item.user_card_id) if item.user_card_id else None
            return TradeSessionItemOut(
                id=item.id, owner_id=item.owner_id, item_type="card",
                card=await build_card_response(session, card) if card else None,
            )
        if item.item_type == "booster":
            booster = await session.get(Booster, item.booster_id)
            bonus = await session.get(UserBonusBooster, item.bonus_id) if item.bonus_id else None
            return TradeSessionItemOut(
                id=item.id, owner_id=item.owner_id, item_type="booster", booster_id=item.booster_id,
                name=booster.name if booster else item.booster_id,
                label=(bonus.label or None) if bonus else None, amount=item.amount,
            )
        if item.item_type == "reroll":
            token = await session.get(UserRerollToken, item.reroll_token_id)
            axes = [_AXIS_LABEL.get(a, a) for a in (reroll_inventory.reroll_axes(token) if token else [])]
            if token and token.reroll_power:
                axes.append("puissance")
            rules = " + ".join(axes) + (" — garanti" if token and token.reroll_mode == "guaranteed_min" else "")
            return TradeSessionItemOut(
                id=item.id, owner_id=item.owner_id, item_type="reroll",
                name=token.label if token else "Reroll", label=rules or None, amount=item.amount,
            )
        resource_name = "Pièces" if item.resource_id == COINS_ID else (
            (await session.get(Resource, item.resource_id)).name
        )
        return TradeSessionItemOut(
            id=item.id, owner_id=item.owner_id, item_type="resource",
            resource_id=item.resource_id, resource_name=resource_name, amount=item.amount,
        )

    my_items = [await _out(i) for i in items if i.owner_id == viewer_id]
    other_items = [await _out(i) for i in items if i.owner_id == other_id]

    my_ready = trade.ready_a if side == "a" else trade.ready_b
    other_ready = trade.ready_b if side == "a" else trade.ready_a
    my_confirmed = trade.confirmed_a if side == "a" else trade.confirmed_b
    other_confirmed = trade.confirmed_b if side == "a" else trade.confirmed_a

    return TradeSessionOut(
        id=trade.id, status=trade.status,
        other_user_id=other.id, other_username=other.username, other_display_name=other.display_name,
        other_online=_is_online(other),
        my_ready=my_ready, other_ready=other_ready,
        my_confirmed=my_confirmed, other_confirmed=other_confirmed,
        my_items=my_items, other_items=other_items,
        updated_at=trade.updated_at,
        removed_items=removed_items or [],
    )
