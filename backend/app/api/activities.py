"""
Routes — activités : présence (bonus de chance, coffre d'absence).
Les autres activités (expéditions, atelier, mini-jeux) s'ajoutent ici.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_admin
from app.core.ratelimit import rate_limit
from app.database import get_session
from app.models.user import User
from app.services import activities_config, presence_bonus

router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/presence")
async def presence_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await presence_bonus.status(session, user)


@router.post("/presence/ping", dependencies=[Depends(rate_limit(10, 60))])
async def presence_ping(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Signal envoyé toutes les 30 s par l'appli tant qu'elle est affichée."""
    return await presence_bonus.ping(session, user)


@router.post("/presence/chest", dependencies=[Depends(rate_limit(10, 60))])
async def claim_absence_chest(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await presence_bonus.claim_chest(session, user)


@admin_router.get("/config")
async def get_activities_config(session: AsyncSession = Depends(get_session)):
    return await activities_config.get_config(session)


@admin_router.put("/config")
async def put_activities_config(values: dict, session: AsyncSession = Depends(get_session)):
    return await activities_config.save_config(session, values)
