"""
Routes social — amis, amis proches, demandes d'ami, demandes d'échange (placeholder).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_, update

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.social import FriendRequest, TradeRequest, CloseFriend
from app.schemas.social import (
    FriendOut, SendFriendRequestBody, FriendRequestOut, FriendRequestsResponse,
    TradeRequestOut, TradeRequestsResponse, SendTradeRequestBody,
)
from app.schemas.trade_session import TradeSessionOut
from app.services.friendship import friendship_between as _friendship_between
from app.services.trade_requests import create_trade_request as _create_trade_request
from app.services.trade_session import create_session as _create_trade_session, build_out as _build_trade_session_out

router = APIRouter()

ONLINE_THRESHOLD_S = 300  # "en ligne" si vu il y a moins de 5 min


def _is_online(user: User) -> bool:
    return bool(user.last_seen and datetime.utcnow() - user.last_seen < timedelta(seconds=ONLINE_THRESHOLD_S))


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
    close_ids = {row.friend_user_id for row in (await session.execute(
        select(CloseFriend).where(CloseFriend.user_id == user.id)
    )).scalars().all()}
    return [
        FriendOut(
            user_id=f.id, username=f.username, display_name=f.display_name,
            online=_is_online(f), last_seen=f.last_seen,
            close_friend=f.id in close_ids,
        )
        for f in friends
    ]


@router.post("/{friend_user_id}/close-friend", status_code=204)
async def add_close_friend(
    friend_user_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Marque un ami existant comme "proche" (à sens unique, pas besoin que l'autre valide)."""
    if not await _friendship_between(session, user.id, friend_user_id):
        raise HTTPException(400, "Vous devez déjà être amis.")
    if not await session.get(CloseFriend, (user.id, friend_user_id)):
        session.add(CloseFriend(user_id=user.id, friend_user_id=friend_user_id))
        await session.commit()


@router.delete("/{friend_user_id}/close-friend", status_code=204)
async def remove_close_friend(
    friend_user_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    row = await session.get(CloseFriend, (user.id, friend_user_id))
    if row:
        await session.delete(row)
        await session.commit()


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
    recréer une (évite deux demandes croisées qui se bloquent) — cette
    résolution passe même si `target` a fermé ses demandes entrantes,
    puisque ce n'est pas une NOUVELLE demande de ta part.
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

    if not target.allow_friend_requests:
        raise HTTPException(403, "Ce joueur n'accepte pas de nouvelles demandes d'ami pour le moment.")

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
    # Le retrait d'amitié invalide aussi un éventuel marquage "ami proche"
    # dans les deux sens (sinon la ligne resterait orpheline en base).
    close_rows = (await session.execute(
        select(CloseFriend).where(
            or_(
                and_(CloseFriend.user_id == user.id, CloseFriend.friend_user_id == friend_user_id),
                and_(CloseFriend.user_id == friend_user_id, CloseFriend.friend_user_id == user.id),
            ),
        )
    )).scalars().all()
    for row in close_rows:
        await session.delete(row)
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

    # Consulter la liste marque les demandes reçues comme vues — le popup de
    # notification (basé sur /trade-requests/unseen) ne les re-signalera plus.
    await session.execute(
        update(TradeRequest)
        .where(TradeRequest.addressee_id == user.id, TradeRequest.status == "pending", TradeRequest.seen == False)  # noqa: E712
        .values(seen=True)
    )
    await session.commit()

    return TradeRequestsResponse(incoming=incoming, outgoing=outgoing)


@router.get("/trade-requests/unseen", response_model=list[TradeRequestOut])
async def list_unseen_trade_requests(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Demandes d'échange reçues pas encore vues — sert au popup de notification.
    Ne marque PAS comme vu (contrairement à GET /trade-requests) : c'est au
    popup de le faire explicitement une fois affiché (POST .../mark-seen).
    """
    rows = (await session.execute(
        select(TradeRequest).where(
            TradeRequest.status == "pending",
            TradeRequest.addressee_id == user.id,
            TradeRequest.seen == False,  # noqa: E712
        )
    )).scalars().all()
    if not rows:
        return []
    other_ids = {r.requester_id for r in rows}
    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_(other_ids))
    )).scalars().all()}
    return [
        TradeRequestOut(
            id=r.id, user_id=users[r.requester_id].id, username=users[r.requester_id].username,
            display_name=users[r.requester_id].display_name, created_at=r.created_at,
        )
        for r in rows if r.requester_id in users
    ]


@router.post("/trade-requests/mark-seen", status_code=204)
async def mark_trade_requests_seen(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(TradeRequest)
        .where(TradeRequest.addressee_id == user.id, TradeRequest.status == "pending")
        .values(seen=True)
    )
    await session.commit()


@router.post(
    "/trade-requests", response_model=TradeRequestOut, status_code=201,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def send_trade_request_by_username(
    body: SendTradeRequestBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Envoie une demande d'échange par pseudo — pas besoin d'être ami au
    préalable (utile pour un échange ponctuel) : ce qui décide si c'est
    accepté, c'est `target.trade_request_policy` (réglable côté destinataire).
    """
    target = (await session.execute(
        select(User).where(User.username == body.username.strip().lower())
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Aucun joueur avec ce pseudo.")

    req = await _create_trade_request(session, user, target)
    return TradeRequestOut(
        id=req.id, user_id=target.id, username=target.username,
        display_name=target.display_name, created_at=req.created_at,
    )


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
    Pose une demande d'échange en attente (variante par id, utilisée depuis
    la liste d'amis). L'échange en lui-même (choix des cartes) n'est pas
    encore implémenté — cette route prépare juste la relation.
    """
    target = await session.get(User, friend_user_id)
    if not target:
        raise HTTPException(404, "Joueur introuvable.")

    req = await _create_trade_request(session, user, target)
    return TradeRequestOut(
        id=req.id, user_id=target.id, username=target.username,
        display_name=target.display_name, created_at=req.created_at,
    )


@router.post("/trade-requests/{request_id}/accept", response_model=TradeSessionOut)
async def accept_trade_request(
    request_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Accepte une demande d'échange reçue : ouvre la session d'échange en direct."""
    req = await session.get(TradeRequest, request_id)
    if not req or req.status != "pending" or req.addressee_id != user.id:
        raise HTTPException(404, "Demande introuvable.")

    trade = await _create_trade_session(session, req.requester_id, req.addressee_id)
    await session.delete(req)
    await session.commit()
    return await _build_trade_session_out(session, trade, user.id)


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
