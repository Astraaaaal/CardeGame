"""
Routes — niveaux, achievements, quêtes.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.progression import LevelStatus, AchievementOut, QuestOut
from app.services import levels as levels_svc
from app.services import achievements as achievements_svc
from app.services import quests as quests_svc

router = APIRouter()


@router.get("/levels", response_model=LevelStatus)
async def get_level_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await levels_svc.get_status(session, user)


@router.post("/levels/claim", response_model=LevelStatus)
async def claim_level(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await levels_svc.claim_level_rewards(session, user)


@router.get("/achievements", response_model=list[AchievementOut])
async def get_achievements(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await achievements_svc.list_achievements(session, user)


@router.post("/achievements/{achievement_id}/claim", response_model=AchievementOut)
async def claim_achievement(
    achievement_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await achievements_svc.claim_achievement(session, user, achievement_id)


@router.get("/quests", response_model=list[QuestOut])
async def get_quests(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await quests_svc.list_quests(session, user.id)


@router.post("/quests/{user_quest_id}/claim", response_model=QuestOut)
async def claim_quest(
    user_quest_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await quests_svc.claim_quest(session, user, user_quest_id)
