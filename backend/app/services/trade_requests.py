"""
Demandes d'échange — création (politique de réception + anti-doublon),
acceptation, et l'état condensé que le client interroge en continu
(`build_pulse`) pour réagir sans rechargement.

Un joueur peut avoir plusieurs propositions en attente vers des joueurs
différents : la première acceptée ouvre la session et annule toutes les
autres propositions envoyées par les deux participants.
"""

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_

from app.models.user import User
from app.models.social import TradeRequest
from app.models.trade_session import TradeSession
from app.schemas.social import TradeRequestOut, TradePulseOut
from app.services.trade_policy import can_send_trade_request
from app.services.trade_session import create_session, get_active_session_for
from app.services import account_email, level_gap, unlocks


async def create_trade_request(session: AsyncSession, requester: User, target: User) -> TradeRequest:
    if requester.id == target.id:
        raise HTTPException(400, "Tu ne peux pas te proposer un échange à toi-même.")
    account_email.require_verified_email(requester)
    if await get_active_session_for(session, requester.id):
        raise HTTPException(409, "Tu as déjà un échange en cours.")
    if not await can_send_trade_request(session, requester.id, target):
        raise HTTPException(403, "Ce joueur n'accepte pas ce type de demande d'échange de ta part.")
    await level_gap.require(session, requester, target, "Impossible d'échanger avec ce joueur.")

    existing = (await session.execute(
        select(TradeRequest).where(
            TradeRequest.status == "pending",
            or_(
                and_(TradeRequest.requester_id == requester.id, TradeRequest.addressee_id == target.id),
                and_(TradeRequest.requester_id == target.id, TradeRequest.addressee_id == requester.id),
            ),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Une demande d'échange est déjà en attente avec ce joueur.")

    await unlocks.require(session, requester, "trades")
    req = TradeRequest(requester_id=requester.id, addressee_id=target.id)
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req


async def accept_trade_request(session: AsyncSession, request_id: int, user_id: int) -> TradeSession:
    req = await session.get(TradeRequest, request_id)
    if not req or req.status != "pending" or req.addressee_id != user_id:
        raise HTTPException(404, "Demande introuvable.")
    addressee = await session.get(User, user_id)
    account_email.require_verified_email(addressee)
    # Revérifié à l'acceptation : les deux niveaux ont pu bouger depuis la demande.
    await level_gap.require(session, await session.get(User, req.requester_id), addressee,
                            "Impossible d'échanger avec ce joueur.")

    participants = [req.requester_id, req.addressee_id]
    trade = await create_session(session, *participants)
    await session.execute(
        delete(TradeRequest).where(
            TradeRequest.status == "pending",
            TradeRequest.requester_id.in_(participants),
        )
    )
    await session.commit()
    return trade


async def build_pulse(session: AsyncSession, user: User) -> TradePulseOut:
    trade = await get_active_session_for(session, user.id)

    rows = (await session.execute(
        select(TradeRequest).where(
            TradeRequest.status == "pending",
            or_(TradeRequest.requester_id == user.id, TradeRequest.addressee_id == user.id),
        ).order_by(TradeRequest.created_at)
    )).scalars().all()

    requester_ids = {r.requester_id for r in rows if r.addressee_id == user.id and not r.seen}
    requesters = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_(requester_ids))
    )).scalars().all()} if requester_ids else {}

    return TradePulseOut(
        active_session_id=trade.id if trade else None,
        incoming_unseen=[
            TradeRequestOut(
                id=r.id, user_id=r.requester_id, username=requesters[r.requester_id].username,
                display_name=requesters[r.requester_id].display_name, created_at=r.created_at,
            )
            for r in rows
            if r.addressee_id == user.id and not r.seen and r.requester_id in requesters
        ],
        incoming_ids=[r.id for r in rows if r.addressee_id == user.id],
        outgoing_ids=[r.id for r in rows if r.requester_id == user.id],
    )
