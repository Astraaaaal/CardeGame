"""
Routes social — amis, amis proches, demandes d'ami, demandes d'échange (placeholder).
"""

from datetime import datetime

from app.services import guilds
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, and_, update, func

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.social import FriendRequest, TradeRequest, CloseFriend, FriendGroup, FriendGroupMember
from app.schemas.social import (
    FriendOut, SendFriendRequestBody, FriendRequestOut, FriendRequestsResponse,
    TradeRequestOut, TradeRequestsResponse, SendTradeRequestBody, TradePulseOut,
    FriendGroupOut, FriendGroupBody,
)
from app.schemas.trade_session import TradeSessionOut
from app.services.friendship import friendship_between as _friendship_between
from app.services import trade_requests as _trade_requests
from app.services.trade_requests import create_trade_request as _create_trade_request
from app.services.trade_session import build_out as _build_trade_session_out
from app.services import quest_progress
from app.services.presence import is_online as _is_online
from app.services import unlocks

router = APIRouter()


class MoveGroupBody(BaseModel):
    direction: int = Field(ge=-1, le=1)

MAX_FRIEND_GROUPS = 15


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
    group_ids_by_friend: dict[int, list[int]] = {}
    for group_id, friend_user_id in (await session.execute(
        select(FriendGroupMember.group_id, FriendGroupMember.friend_user_id)
        .join(FriendGroup, FriendGroup.id == FriendGroupMember.group_id)
        .where(FriendGroup.user_id == user.id)
    )).all():
        group_ids_by_friend.setdefault(friend_user_id, []).append(group_id)
    guild_tags = await guilds.tags_for(session, [f.id for f in friends])
    return [
        FriendOut(
            user_id=f.id, username=f.username, display_name=f.display_name,
            online=_is_online(f), last_seen=f.last_seen,
            close_friend=f.id in close_ids,
            group_ids=group_ids_by_friend.get(f.id, []),
            guild=guild_tags.get(f.id),
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


@router.get("/groups", response_model=list[FriendGroupOut])
async def list_friend_groups(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (await session.execute(
        select(FriendGroup).where(FriendGroup.user_id == user.id).order_by(FriendGroup.position, FriendGroup.id)
    )).scalars().all()
    return [FriendGroupOut(id=g.id, name=g.name) for g in rows]


@router.post("/groups/{group_id}/move", response_model=list[FriendGroupOut])
async def move_friend_group(
    group_id: int,
    body: MoveGroupBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Monte (-1) ou descend (+1) un groupe dans la liste ; renvoie la liste réordonnée."""
    rows = list((await session.execute(
        select(FriendGroup).where(FriendGroup.user_id == user.id).order_by(FriendGroup.position, FriendGroup.id)
    )).scalars().all())
    index = next((i for i, g in enumerate(rows) if g.id == group_id), None)
    if index is None:
        raise HTTPException(404, "Groupe introuvable.")
    target = index + body.direction
    if 0 <= target < len(rows):
        rows[index], rows[target] = rows[target], rows[index]
    for pos, g in enumerate(rows):
        g.position = pos
        session.add(g)
    await session.commit()
    return [FriendGroupOut(id=g.id, name=g.name) for g in rows]


@router.post("/groups", response_model=FriendGroupOut, status_code=201)
async def create_friend_group(
    body: FriendGroupBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    count = (await session.execute(
        select(func.count()).select_from(FriendGroup).where(FriendGroup.user_id == user.id)
    )).scalar() or 0
    if count >= MAX_FRIEND_GROUPS:
        raise HTTPException(400, f"Maximum {MAX_FRIEND_GROUPS} groupes.")
    group = FriendGroup(user_id=user.id, name=body.name.strip(), position=count)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    return FriendGroupOut(id=group.id, name=group.name)


@router.patch("/groups/{group_id}", response_model=FriendGroupOut)
async def rename_friend_group(
    group_id: int,
    body: FriendGroupBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group = await session.get(FriendGroup, group_id)
    if not group or group.user_id != user.id:
        raise HTTPException(404, "Groupe introuvable.")
    group.name = body.name.strip()
    session.add(group)
    await session.commit()
    return FriendGroupOut(id=group.id, name=group.name)


@router.delete("/groups/{group_id}", status_code=204)
async def delete_friend_group(
    group_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group = await session.get(FriendGroup, group_id)
    if not group or group.user_id != user.id:
        raise HTTPException(404, "Groupe introuvable.")
    await session.delete(group)
    await session.commit()


@router.post("/{friend_user_id}/groups/{group_id}", status_code=204)
async def add_friend_to_group(
    friend_user_id: int,
    group_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group = await session.get(FriendGroup, group_id)
    if not group or group.user_id != user.id:
        raise HTTPException(404, "Groupe introuvable.")
    if not await _friendship_between(session, user.id, friend_user_id):
        raise HTTPException(400, "Vous devez déjà être amis.")
    if not await session.get(FriendGroupMember, (group_id, friend_user_id)):
        session.add(FriendGroupMember(group_id=group_id, friend_user_id=friend_user_id))
        await session.commit()


@router.delete("/{friend_user_id}/groups/{group_id}", status_code=204)
async def remove_friend_from_group(
    friend_user_id: int,
    group_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    group = await session.get(FriendGroup, group_id)
    if not group or group.user_id != user.id:
        raise HTTPException(404, "Groupe introuvable.")
    row = await session.get(FriendGroupMember, (group_id, friend_user_id))
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
    await quest_progress.increment(session, user.id, "friend_requests_sent", 1)
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
        guild=(await guilds.tags_for(session, [other.id])).get(other.id),
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

    # Même nettoyage pour les groupes personnalisés : retire l'ex-ami des
    # groupes de l'utilisateur, et l'utilisateur des groupes de l'ex-ami.
    group_member_rows = (await session.execute(
        select(FriendGroupMember)
        .join(FriendGroup, FriendGroup.id == FriendGroupMember.group_id)
        .where(
            or_(
                and_(FriendGroup.user_id == user.id, FriendGroupMember.friend_user_id == friend_user_id),
                and_(FriendGroup.user_id == friend_user_id, FriendGroupMember.friend_user_id == user.id),
            ),
        )
    )).scalars().all()
    for row in group_member_rows:
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

    # Pas de "vu" ici : la liste est aussi chargée depuis l'onglet Amis (état
    # "échange en attente" des boutons), ça étoufferait le popup. C'est
    # l'affichage de l'onglet Échanges qui marque vu (POST .../mark-seen).
    return TradeRequestsResponse(incoming=incoming, outgoing=outgoing)


@router.get("/trade-requests/pulse", response_model=TradePulseOut)
async def trade_pulse(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Interrogé en continu par le client : échange lancé (pour y entrer
    automatiquement), demandes reçues à afficher, ids pour rafraîchir les listes."""
    return await _trade_requests.build_pulse(session, user)


@router.post("/trade-requests/mark-seen", status_code=204)
async def mark_trade_requests_seen(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Onglet Échanges affiché : les demandes reçues y sont visibles, le popup
    n'a plus à les signaler."""
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
    """Accepte une demande d'échange reçue : ouvre la session d'échange en
    direct et annule les autres propositions envoyées par les deux joueurs."""
    await unlocks.require(session, user, "trades")
    trade = await _trade_requests.accept_trade_request(session, request_id, user.id)
    return await _build_trade_session_out(session, trade, user.id)


@router.post("/trade-requests/{request_id}/seen", status_code=204)
async def mark_trade_request_seen(
    request_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """"Plus tard" depuis le popup : la demande reste en attente dans l'onglet
    Échanges mais n'est plus signalée."""
    req = await session.get(TradeRequest, request_id)
    if not req or req.status != "pending" or req.addressee_id != user.id:
        raise HTTPException(404, "Demande introuvable.")
    req.seen = True
    session.add(req)
    await session.commit()


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
