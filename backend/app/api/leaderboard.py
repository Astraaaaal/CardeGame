"""
Classements de puissance — somme de UserCard.power par joueur (cf.
app/services/power.py) : entre amis, top 10 global, top 10 par type de
personnage.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, or_

from app.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character, CharacterType
from app.models.social import FriendRequest
from app.schemas.leaderboard import LeaderboardEntry, LeaderboardResponse
from app.services.ranking import record_rank

router = APIRouter()


async def _leaderboard(
    session: AsyncSession,
    user_ids: Optional[list[int]],
    type_name: Optional[str],
    limit: Optional[int],
) -> list[LeaderboardEntry]:
    """
    user_ids=None -> pas de restriction (classement global) ; [] -> aucun résultat.
    type_name -> ne compte que les cartes des personnages de ce type.
    """
    if user_ids is not None and not user_ids:
        return []

    query = (
        select(UserCard.user_id, func.sum(UserCard.power))
        .where(UserCard.power != None)  # noqa: E711
        .group_by(UserCard.user_id)
    )
    if user_ids is not None:
        query = query.where(UserCard.user_id.in_(user_ids))
    if type_name:
        query = query.join(Character, Character.id == UserCard.character_id).where(Character.type == type_name)
    query = query.order_by(func.sum(UserCard.power).desc())
    if limit:
        query = query.limit(limit)

    rows = (await session.execute(query)).all()
    if not rows:
        return []

    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_([r[0] for r in rows]))
    )).scalars().all()}

    entries = []
    for i, (uid, total) in enumerate(rows, start=1):
        u = users.get(uid)
        if not u:
            continue
        entries.append(LeaderboardEntry(
            rank=i, user_id=u.id, username=u.username, display_name=u.display_name,
            total_power=int(total or 0),
        ))
    return entries


@router.get("/friends", response_model=LeaderboardResponse)
async def leaderboard_friends(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Classement de puissance totale entre toi et tes amis."""
    rows = (await session.execute(
        select(FriendRequest).where(
            FriendRequest.status == "accepted",
            or_(FriendRequest.requester_id == user.id, FriendRequest.addressee_id == user.id),
        )
    )).scalars().all()
    friend_ids = [(r.addressee_id if r.requester_id == user.id else r.requester_id) for r in rows]
    entries = await _leaderboard(session, [user.id, *friend_ids], None, None)
    return LeaderboardResponse(entries=entries)


@router.get("/global", response_model=LeaderboardResponse)
async def leaderboard_global(
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Top 10 des joueurs par puissance totale, tous joueurs confondus."""
    entries = await _leaderboard(session, None, None, 10)
    ranked = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_([e.user_id for e in entries]))
    )).scalars().all()} if entries else {}
    changed = [ranked[e.user_id] for e in entries if e.user_id in ranked and record_rank(ranked[e.user_id], e.rank)]
    if changed:
        session.add_all(changed)
        await session.commit()
    return LeaderboardResponse(entries=entries)


@router.get("/by-type", response_model=LeaderboardResponse)
async def leaderboard_by_type(
    type_name: str,
    _user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Top 10 des joueurs par puissance totale, restreinte aux cartes d'un type de personnage."""
    exists = (await session.execute(
        select(CharacterType).where(CharacterType.name == type_name)
    )).scalar_one_or_none()
    if not exists:
        raise HTTPException(404, f"Type '{type_name}' introuvable.")
    entries = await _leaderboard(session, None, type_name, 10)
    return LeaderboardResponse(entries=entries)
