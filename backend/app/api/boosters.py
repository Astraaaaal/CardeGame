"""
Routes boosters — Liste et ouverture de packs.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.booster import Booster
from app.schemas.booster import BoosterResponse, PackOpenRequest, PackOpenResponse
from app.services.pack_service import PackService

router = APIRouter()
pack_service = PackService()


@router.get("/", response_model=list[BoosterResponse])
async def list_boosters(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Liste tous les boosters disponibles à l'achat."""
    result = await session.execute(select(Booster))
    boosters = result.scalars().all()
    return [
        BoosterResponse(
            id=b.id,
            name=b.name,
            set_id=b.set_id,
            cards_count=b.cards_count,
            price=b.price,
            guaranteed_rare=b.guaranteed_rare,
            description=b.description,
        )
        for b in boosters
    ]


@router.post(
    "/open",
    response_model=PackOpenResponse,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def open_packs(
    request: PackOpenRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Ouvre un ou plusieurs packs (1, 5, ou 10).
    Toute la logique est côté serveur (anti-triche).
    """
    result = await pack_service.open_packs(
        session,
        user_id=user.id,
        booster_id=request.booster_id,
        quantity=request.quantity,
    )
    return PackOpenResponse(**result)
