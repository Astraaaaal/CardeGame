"""
Routes social — amis, demandes d'ami, demandes d'échange (placeholder).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.social import FriendRequest, TradeRequest
from app.schemas.social import (
    FriendOut, SendFriendRequestBody, FriendRequestOut, FriendRequestsResponse,
    TradeRequestOut, TradeRequestsResponse,
)

router = APIRouter()

ONLINE_THRESHOLD_S = 300  # "en ligne" si vu il y a moins de 5 min


def _is_online(user: User) -> bool:
    return bool(user.last_seen and datetime.utcnow() - user.last_seen < timedelta(seconds=ONLINE_THRESHOLD_S))


async def _friendship_between(session: AsyncSession, a: int, b: int) -> FriendRequest | None:
    return (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(
                and_(FriendRequest.requester_id == a, FriendRequest.addressee_id == b),
                and_(FriendRequest.requester_id == b, FriendRequest.addressee_id == a),
            ),
        )
    )).scalar_one_or_none()


@router.get("/", response_model=list[FriendOut])
async def list_friends(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Liste des amis (demandes acceptées), avec statut en ligne dérivé de last_seen."""
    rows = (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(FriendRequest.requester_id == user.id, FriendRequest.addressee_id == user.id),
        )
    )).scalars().all()
    friend_ids = [
        (r.addressee_id if r.requester_id == user.id else r.requester_id) for r in rows
    ]
    if not friend_ids:
        return []
    friends = (await session.execute(select(User).where(User.id.in_(friend_ids)))).scalars().all()
    return [
        FriendOut(
            user_id=f.id, username=f.username, display_name=f.display_name,
            online=_is_online(f), last_seen=f.last_seen,
        )
        for f in friends
    ]


@router.get("/requests", response_model=FriendRequestsResponse)
async def list_friend_requests(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Demandes d'ami en attente, reçues et envoyées."""
    rows = (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "pending",
            or_(FriendRequest.requester_id == user.id, FriendRequest.addressee_id == user.id),
        )
    )).scalars().all()
    other_ids = {(r.addressee_id if r.requester_id == user.id else r.requester_id) for r in rows}
    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_(other_ids))
    )).scalars().all()} if other_ids else {}

    incoming, outgoing = [], []
    for r in rows:
        is_incoming = r.addressee_id == user.id
        other = users.get(r.requester_id if is_incoming else r.addressee_id)
        if not other:
            continue
        item = FriendRequestOut(
            id=r.id, user_id=other.id, username=other.username,
            display_name=other.display_name, created_at=r.created_at,
        )
        (incoming if is_incoming else outgoing).append(item)
    return FriendRequestsResponse(incoming=incoming, outgoing=outgoing)


@router.post(
    "/requests", response_model=FriendRequestOut, status_code=201,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def send_friend_request(
    body: SendFriendRequestBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Envoie une demande d'ami par pseudo. Si l'autre joueur a déjà une
    demande en attente vers toi, l'accepte directement au lieu d'en
    recréer une (évite deux demandes croisées qui se bloquent).
    """
    target = (await session.execute(
        select(User).where(User.username == body.username)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Aucun joueur avec ce pseudo.")
    if target.id == user.id:
        raise HTTPException(400, "Tu ne peux pas t'ajouter toi-même.")

    if await _friendship_between(session, user.id, target.id):
        raise HTTPException(409, f"{target.display_name} est déjà dans tes amis.")

    reverse = (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "pending",
            FriendRequest.requester_id == target.id,
            FriendRequest.addressee_id == user.id,
        )
    )).scalar_one_or_none()
    if reverse:
        reverse.status = "accepted"
        reverse.responded_at = datetime.utcnow()
        session.add(reverse)
        await session.commit()
        return FriendRequestOut(
            id=reverse.id, user_id=target.id, username=target.username,
            display_name=target.display_name, created_at=reverse.created_at,
        )

    existing = (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "pending",
            FriendRequest.requester_id == user.id,
            FriendRequest.addressee_id == target.id,
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Demande déjà envoyée, en attente de réponse.")

    req = FriendRequest(requester_id=user.id, addressee_id=target.id)
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return FriendRequestOut(
        id=req.id, user_id=target.id, username=target.username,
        display_name=target.display_name, created_at=req.created_at,
    )


@router.post("/requests/{request_id}/accept", response_model=FriendOut)
async def accept_friend_request(
    request_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    req = await session.get(FriendRequest, request_id)
    if not req or req.status != "pending" or req.addressee_id != user.id:
        raise HTTPException(404, "Demande introuvable.")
    req.status = "accepted"
    req.responded_at = datetime.utcnow()
    session.add(req)
    await session.commit()
    other = await session.get(User, req.requester_id)
    return FriendOut(
        user_id=other.id, username=other.username, display_name=other.display_name,
        online=_is_online(other), last_seen=other.last_seen,
    )


@router.delete("/requests/{request_id}", status_code=204)
async def remove_friend_request(
    request_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Refuse une demande reçue, ou annule une demande envoyée (même action des deux côtés)."""
    req = await session.get(FriendRequest, request_id)
    if not req or req.status != "pending" or user.id not in (req.requester_id, req.addressee_id):
        raise HTTPException(404, "Demande introuvable.")
    await session.delete(req)
    await session.commit()


@router.delete("/{friend_user_id}", status_code=204)
async def remove_friend(
    friend_user_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    friendship = await _friendship_between(session, user.id, friend_user_id)
    if not friendship:
        raise HTTPException(404, "Vous n'êtes pas amis.")
    await session.delete(friendship)
    await session.commit()


# ─────────────────────  Demandes d'échange (placeholder)  ─────────────────

@router.get("/trade-requests", response_model=TradeRequestsResponse)
async def list_trade_requests(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(TradeRequest).where(
            TradeRequest.status == "pending",
            or_(TradeRequest.requester_id == user.id, TradeRequest.addressee_id == user.id),
        )
    )).scalars().all()
    other_ids = {(r.addressee_id if r.requester_id == user.id else r.requester_id) for r in rows}
    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_(other_ids))
    )).scalars().all()} if other_ids else {}

    incoming, outgoing = [], []
    for r in rows:
        is_incoming = r.addressee_id == user.id
        other = users.get(r.requester_id if is_incoming else r.addressee_id)
        if not other:
            continue
        item = TradeRequestOut(
            id=r.id, user_id=other.id, username=other.username,
            display_name=other.display_name, created_at=r.created_at,
        )
        (incoming if is_incoming else outgoing).append(item)
    return TradeRequestsResponse(incoming=incoming, outgoing=outgoing)


@router.post(
    "/{friend_user_id}/trade-request", response_model=TradeRequestOut, status_code=201,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def create_trade_request(
    friend_user_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Pose une demande d'échange en attente. L'échange en lui-même (choix des
    cartes) n'est pas encore implémenté — cette route prépare juste la relation.
    """
    if not await _friendship_between(session, user.id, friend_user_id):
        raise HTTPException(403, "Vous devez être amis pour proposer un échange.")

    existing = (await session.execute(
        select(TradeRequest).where(
            TradeRequest.status == "pending",
            or_(
                and_(TradeRequest.requester_id == user.id, TradeRequest.addressee_id == friend_user_id),
                and_(TradeRequest.requester_id == friend_user_id, TradeRequest.addressee_id == user.id),
            ),
        )
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "Une demande d'échange est déjà en attente avec cet ami.")

    target = await session.get(User, friend_user_id)
    if not target:
        raise HTTPException(404, "Joueur introuvable.")

    req = TradeRequest(requester_id=user.id, addressee_id=friend_user_id)
    session.add(req)
    await session.commit()
    await session.refresh(req)
    return TradeRequestOut(
        id=req.id, user_id=target.id, username=target.username,
        display_name=target.display_name, created_at=req.created_at,
    )


@router.delete("/trade-requests/{request_id}", status_code=204)
async def remove_trade_request(
    request_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Annule (côté demandeur) ou refuse (côté destinataire) une demande d'échange."""
    req = await session.get(TradeRequest, request_id)
    if not req or req.status != "pending" or user.id not in (req.requester_id, req.addressee_id):
        raise HTTPException(404, "Demande introuvable.")
    await session.delete(req)
    await session.commit()
