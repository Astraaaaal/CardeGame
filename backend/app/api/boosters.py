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
from app.models.booster import Booster, BoosterSet
from app.models.economy import Resource
from app.schemas.booster import BoosterResponse, PackOpenRequest, PackOpenResponse, OpenOwnedRequest, OwnedBoosterOut
from app.services.pack_service import PackService
from app.services import booster_inventory
from app.services.ranking import refresh_all_best_ranks

router = APIRouter()
pack_service = PackService()


@router.get("/", response_model=list[BoosterResponse])
async def list_boosters(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Liste les boosters disponibles à l'achat en pièces (actifs et visibles)."""
    result = await session.execute(
        select(Booster).where(Booster.active == True, Booster.visible_in_shop == True)  # noqa: E712
    )
    boosters = result.scalars().all()
    links = (await session.execute(select(BoosterSet))).scalars().all()
    sets_by_booster: dict[str, list[str]] = {}
    for link in links:
        sets_by_booster.setdefault(link.booster_id, []).append(link.set_id)

    resources = {r.id: r.name for r in (await session.execute(select(Resource))).scalars().all()}

    return [
        BoosterResponse(
            id=b.id,
            name=b.name,
            set_id=b.set_id,
            set_ids=sets_by_booster.get(b.id) or [b.set_id],
            cards_count=b.cards_count,
            resource_id=b.resource_id,
            resource_name=resources.get(b.resource_id, b.resource_id),
            price=b.price,
            guaranteed_rare=b.guaranteed_rare,
            description=b.description,
            cover_image_url=b.cover_image_url,
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
    await refresh_all_best_ranks(session)
    await session.commit()
    return PackOpenResponse(**result)


@router.get("/inventory", response_model=list[OwnedBoosterOut])
async def list_owned_boosters(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Boosters reçus en récompense (achievements, niveaux...) pas encore ouverts."""
    return await booster_inventory.list_owned(session, user.id)


@router.post(
    "/inventory/open",
    response_model=PackOpenResponse,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def open_owned_boosters(
    request: OpenOwnedRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Ouvre des boosters déjà possédés (gratuit — même flux/animation qu'un achat)."""
    result = await booster_inventory.open_owned(session, user, request.booster_id, request.quantity)
    await refresh_all_best_ranks(session)
    await session.commit()
    return PackOpenResponse(**result)
