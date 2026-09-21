"""
Logique de la messagerie — inbox, récupération de récompense, envoi de
cadeau entre joueurs, diffusion admin.
"""

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.user import User
from app.models.card import UserCard
from app.models.economy import Resource
from app.models.booster import Booster
from app.models.message import Message
from app.schemas.message import MessageOut
from app.services.card_view import build_card_response
from app.services.wallet import get_balance, apply_delta, COINS_ID
from app.services.gift_policy import can_send_gift
from app.services import quest_progress
from app.services import booster_inventory, expeditions, message_rewards, reroll_inventory
from app.services.premium import ensure_tradeable
from app.services import favorites

MAX_RECIPIENTS_PER_SEND = 200


async def list_inbox(session: AsyncSession, user_id: int) -> list[Message]:
    rows = (await session.execute(
        select(Message).where(Message.recipient_user_id == user_id).order_by(Message.created_at.desc())
    )).scalars().all()
    return rows


async def unread_count(session: AsyncSession, user_id: int) -> int:
    rows = (await session.execute(
        select(Message.id).where(Message.recipient_user_id == user_id, Message.read_at.is_(None))
    )).all()
    return len(rows)


async def get_message_or_404(session: AsyncSession, message_id: int, user_id: int) -> Message:
    msg = await session.get(Message, message_id)
    if not msg or msg.recipient_user_id != user_id:
        raise HTTPException(404, "Message introuvable.")
    return msg


async def mark_read(session: AsyncSession, message: Message) -> Message:
    if not message.read_at:
        message.read_at = datetime.utcnow()
        session.add(message)
        await session.commit()
        await session.refresh(message)
    return message


def _has_reward(message: Message) -> bool:
    return (
        bool(message.reward_card_id)
        or bool(message.reward_resource_id and message.reward_amount)
        or bool(message.reward_booster_id and message.reward_booster_qty)
        or bool(message.reward_reroll and message.reward_reroll.get("quantity"))
        or bool(message.reward_items)
    )


def _has_unclaimed_reward(message: Message) -> bool:
    return _has_reward(message) and not message.claimed_at


async def delete_message(session: AsyncSession, message: Message) -> None:
    if _has_unclaimed_reward(message):
        raise HTTPException(400, "Récupère la récompense avant de supprimer ce message.")
    await session.delete(message)
    await session.commit()


async def claim(session: AsyncSession, message: Message) -> Message:
    if message.claimed_at:
        raise HTTPException(409, "Récompense déjà récupérée.")
    if not _has_reward(message):
        raise HTTPException(400, "Ce message ne contient pas de récompense.")

    recipient = await session.get(User, message.recipient_user_id)
    error = None

    if message.reward_card_id:
        card = (await session.execute(
            select(UserCard).where(UserCard.id == message.reward_card_id).with_for_update()
        )).scalar_one_or_none()
        if not card or (message.sender_user_id and card.user_id != message.sender_user_id) \
                or await expeditions.locked_card_ids(session, [message.reward_card_id]):
            error = "Cette carte n'est plus disponible."
        else:
            card.user_id = recipient.id
            await favorites.release(session, card)
            session.add(card)
            recipient.total_cards += 1
            session.add(recipient)

    if not error and message.reward_resource_id and message.reward_amount:
        await apply_delta(session, recipient, message.reward_resource_id, message.reward_amount)

    if not error and message.reward_booster_id and message.reward_booster_qty:
        bonus = message.reward_booster_bonus
        if bonus:
            await booster_inventory.grant_bonus(
                session, recipient.id, message.reward_booster_id,
                bonus.get("force_min_rarity_id"), bonus.get("rarity_weight_multiplier"),
                bonus.get("label") or "", message.reward_booster_qty, extras=booster_inventory.extra_bonus(bonus),
            )
        else:
            await booster_inventory.grant(session, recipient.id, message.reward_booster_id, message.reward_booster_qty)

    if not error and message.reward_reroll and message.reward_reroll.get("quantity"):
        reroll = message.reward_reroll
        await reroll_inventory.grant_rules(
            session, recipient.id, reroll.get("offer_id"), reroll.get("label") or "Reroll",
            reroll.get("rules") or {}, int(reroll["quantity"]),
        )

    if not error and message.reward_items:
        # Réaffectation (pas de mutation en place) pour que la colonne JSON soit bien enregistrée.
        message.reward_items = await message_rewards.grant(session, recipient, message.reward_items)

    message.claimed_at = datetime.utcnow()
    message.claim_error = error
    if not message.read_at:
        message.read_at = message.claimed_at
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def send_gift(
    session: AsyncSession, sender: User, target_username: str, subject: str, body: str,
    item_type: str, user_card_id: str | None, resource_id: str | None, amount: int | None,
    booster_id: str | None = None, bonus_id: int | None = None, reroll_token_id: int | None = None,
) -> Message:
    if item_type not in ("card", "resource", "booster", "reroll"):
        raise HTTPException(400, "Type de cadeau invalide.")

    target = (await session.execute(
        select(User).where(User.username == target_username.strip().lower())
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Aucun joueur avec ce pseudo.")
    if target.id == sender.id:
        raise HTTPException(400, "Tu ne peux pas t'envoyer un cadeau à toi-même.")
    if not await can_send_gift(session, sender.id, target):
        raise HTTPException(403, "Ce joueur n'accepte pas de cadeaux de ta part pour le moment.")

    reward_card_id = None
    reward_resource_id = None
    reward_amount = None
    reward_booster_id = None
    reward_booster_qty = None
    reward_booster_bonus = None
    reward_reroll = None

    if item_type == "card":
        if not user_card_id:
            raise HTTPException(400, "Carte manquante.")
        card = await session.get(UserCard, user_card_id)
        if not card or card.user_id != sender.id:
            raise HTTPException(404, "Tu ne possèdes pas cette carte.")
        await expeditions.ensure_not_on_expedition(session, [user_card_id])
        reward_card_id = user_card_id
    elif item_type == "booster":
        if not booster_id or not amount or amount <= 0:
            raise HTTPException(400, "Booster ou quantité invalide.")
        if not await session.get(Booster, booster_id):
            raise HTTPException(404, "Booster introuvable.")
        # Débité tout de suite (le cadeau est déjà "engagé"), crédité à la récupération.
        if bonus_id is not None:
            row = await booster_inventory.consume_bonus(session, sender.id, bonus_id, amount)
            if row.booster_id != booster_id:
                raise HTTPException(400, "Booster invalide.")
            reward_booster_bonus = {
                "force_min_rarity_id": row.force_min_rarity_id,
                "rarity_weight_multiplier": row.rarity_weight_multiplier,
                "label": row.label,
                **booster_inventory.extra_bonus(row),
            }
        else:
            await booster_inventory.consume(session, sender.id, booster_id, amount)
        reward_booster_id = booster_id
        reward_booster_qty = amount
    elif item_type == "reroll":
        if not reroll_token_id or not amount or amount <= 0:
            raise HTTPException(400, "Reroll ou quantité invalide.")
        # Débité tout de suite, crédité à la récupération avec les mêmes règles.
        token = await reroll_inventory.consume(session, sender.id, reroll_token_id, amount)
        reward_reroll = {
            "label": token.label, "offer_id": token.offer_id,
            "rules": reroll_inventory.rules_of(token), "quantity": amount,
        }
    else:
        if not resource_id or not amount or amount <= 0:
            raise HTTPException(400, "Ressource ou quantité invalide.")
        if resource_id != COINS_ID and not await session.get(Resource, resource_id):
            raise HTTPException(404, "Ressource introuvable.")
        await ensure_tradeable(session, resource_id)
        balance = await get_balance(session, sender, resource_id)
        if amount > balance:
            raise HTTPException(400, f"Solde insuffisant ({balance}).")
        # Débité tout de suite (le cadeau est déjà "engagé"), crédité à la récupération.
        await apply_delta(session, sender, resource_id, -amount)
        reward_resource_id = resource_id
        reward_amount = amount

    msg = Message(
        sender_type="player", sender_user_id=sender.id, recipient_user_id=target.id,
        subject=subject.strip() or "Cadeau", body=body.strip(),
        reward_resource_id=reward_resource_id, reward_amount=reward_amount, reward_card_id=reward_card_id,
        reward_booster_id=reward_booster_id, reward_booster_qty=reward_booster_qty,
        reward_booster_bonus=reward_booster_bonus, reward_reroll=reward_reroll,
    )
    session.add(msg)
    await quest_progress.increment(session, sender.id, "gifts_sent", 1)
    await session.commit()
    await session.refresh(msg)
    return msg


async def send_admin_broadcast(
    session: AsyncSession, usernames: list[str] | None, subject: str, body: str,
    reward_resource_id: str | None, reward_amount: int | None, rewards: list[dict] | None = None,
) -> int:
    reward_items = await message_rewards.validate(session, rewards) if rewards else None
    if reward_resource_id and reward_resource_id != COINS_ID and not await session.get(Resource, reward_resource_id):
        raise HTTPException(404, "Ressource introuvable.")
    if (reward_resource_id and not reward_amount) or (reward_amount and not reward_resource_id):
        raise HTTPException(400, "Ressource et quantité de récompense doivent être fournies ensemble.")

    if usernames:
        clean = [u.strip().lower() for u in usernames if u.strip()]
        recipients = (await session.execute(select(User).where(User.username.in_(clean)))).scalars().all()
        if not recipients:
            raise HTTPException(404, "Aucun joueur trouvé pour ces pseudos.")
    else:
        recipients = (await session.execute(select(User))).scalars().all()

    if len(recipients) > MAX_RECIPIENTS_PER_SEND:
        raise HTTPException(400, f"Trop de destinataires ({len(recipients)} > {MAX_RECIPIENTS_PER_SEND}).")

    for user in recipients:
        session.add(Message(
            sender_type="admin", sender_user_id=None, recipient_user_id=user.id,
            subject=subject.strip(), body=body.strip(),
            reward_resource_id=reward_resource_id, reward_amount=reward_amount,
            reward_items=reward_items,
        ))
    await session.commit()
    return len(recipients)


async def build_out(session: AsyncSession, message: Message) -> MessageOut:
    sender_name = "Administration"
    if message.sender_type == "player" and message.sender_user_id:
        sender = await session.get(User, message.sender_user_id)
        sender_name = sender.display_name if sender else "Un joueur"

    reward_resource_name = None
    if message.reward_resource_id:
        reward_resource_name = "Pièces" if message.reward_resource_id == COINS_ID else (
            (await session.get(Resource, message.reward_resource_id)).name
        )

    reward_card = None
    if message.reward_card_id:
        card = await session.get(UserCard, message.reward_card_id)
        if card:
            reward_card = await build_card_response(session, card)

    reward_booster_name = None
    reward_booster_cover_url = None
    if message.reward_booster_id:
        booster = await session.get(Booster, message.reward_booster_id)
        if booster:
            reward_booster_name = booster.name
            reward_booster_cover_url = booster.cover_image_url or None

    has_reward = _has_reward(message)

    return MessageOut(
        id=message.id, sender_type=message.sender_type, sender_display_name=sender_name,
        subject=message.subject, body=message.body,
        reward_resource_id=message.reward_resource_id, reward_resource_name=reward_resource_name,
        reward_amount=message.reward_amount, reward_card=reward_card, has_reward=has_reward,
        reward_booster_id=message.reward_booster_id, reward_booster_name=reward_booster_name,
        reward_booster_cover_url=reward_booster_cover_url, reward_booster_qty=message.reward_booster_qty,
        reward_booster_label=(message.reward_booster_bonus or {}).get("label") or None,
        reward_reroll_label=(message.reward_reroll or {}).get("label") or None,
        reward_reroll_qty=(message.reward_reroll or {}).get("quantity") or None,
        reward_items=await message_rewards.describe(session, message.reward_items),
        created_at=message.created_at, read_at=message.read_at, claimed_at=message.claimed_at,
        claim_error=message.claim_error,
    )
