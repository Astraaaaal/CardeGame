"""
Routes joueur — Profil, daily reward.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.token import RefreshToken
from app.models.economy import Resource, UserResource
from app.schemas.player import PlayerResponse, DailyRewardResponse, UpdateProfileRequest
from app.schemas.auth import ChangePasswordRequest, MessageResponse
from app.schemas.economy import ResourceBalance
from app.services.daily_reward import DailyRewardService

router = APIRouter()
daily_service = DailyRewardService()


async def _profile_response(session: AsyncSession, user: User) -> PlayerResponse:
    resources = (await session.execute(
        select(UserResource, Resource.name)
        .join(Resource, Resource.id == UserResource.resource_id)
        .where(UserResource.user_id == user.id)
    )).all()

    return PlayerResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        coins=user.coins,
        packs_opened=user.packs_opened,
        total_cards=user.total_cards,
        login_streak=user.login_streak,
        created_at=user.created_at,
        last_login=user.last_login,
        resources=[
            ResourceBalance(id=ur.resource_id, name=name, amount=ur.amount)
            for ur, name in resources
        ],
    )


@router.get("/me", response_model=PlayerResponse)
async def get_profile(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Retourne le profil du joueur connecté, y compris ses ressources."""
    return await _profile_response(session, user)


@router.patch("/me", response_model=PlayerResponse)
async def update_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Modifie le profil du joueur (pour l'instant : le nom affiché)."""
    user.display_name = body.display_name.strip()
    session.add(user)
    await session.commit()
    return await _profile_response(session, user)


@router.post(
    "/change-password",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(5, 60))],
)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Change le mot de passe. Révoque tous les refresh tokens existants (y
    compris ceux d'autres appareils) — par sécurité, chaque session doit se
    reconnecter avec le nouveau mot de passe.
    """
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Mot de passe actuel incorrect.")

    user.password_hash = hash_password(body.new_password)
    session.add(user)
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await session.commit()
    return MessageResponse(message="Mot de passe changé. Reconnecte-toi.")


@router.post("/daily-reward", response_model=DailyRewardResponse)
async def claim_daily_reward(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Réclame la récompense journalière (streak)."""
    result = await daily_service.check_and_claim(session, user)
    return DailyRewardResponse(**result)
