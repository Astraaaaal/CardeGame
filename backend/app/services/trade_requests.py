"""
Création d'une TradeRequest — factorisé (politique de réception + anti-
doublon) pour être réutilisé par les 3 points d'entrée : envoi par pseudo,
bouton "proposer un échange" sur un ami, et clic sur une carte à échanger
listée en mode "offer".
"""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_

from app.models.user import User
from app.models.social import TradeRequest
from app.services.trade_policy import can_send_trade_request


async def create_trade_request(session: AsyncSession, requester: User, target: User) -> TradeRequest:
    if requester.id == target.id:
        raise HTTPException(400, "Tu ne peux pas te proposer un échange à toi-même.")
    if not await can_send_trade_request(session, requester.id, target):
        raise HTTPException(403, "Ce joueur n'accepte pas ce type de demande d'échange de ta part.")

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

    req = TradeRequest(requester_id=requester.id, addressee_id=target.id)
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return req
