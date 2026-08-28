"""
Routes joueur — Profil, daily reward.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.player import PlayerResponse, DailyRewardResponse
from app.services.daily_reward import DailyRewardService

router = APIRouter()
daily_service = DailyRewardService()


@router.get("/me", response_model=PlayerResponse)
async def get_profile(
    user: User = Depends(get_current_user),
):
    """Retourne le profil du joueur connecté."""
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
    )


@router.post("/daily-reward", response_model=DailyRewardResponse)
async def claim_daily_reward(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Réclame la récompense journalière (streak)."""
    result = await daily_service.check_and_claim(session, user)
    return DailyRewardResponse(**result)
