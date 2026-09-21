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
from pydantic import BaseModel, Field

from app.services import activities_config, expeditions, machine, minigames, presence_bonus, workshop
from app.services import unlocks

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
    await unlocks.require(session, user, "absence_chest")
    return await presence_bonus.claim_chest(session, user)


class ExpeditionStartBody(BaseModel):
    slot: int = Field(ge=0)
    duration_minutes: int = Field(ge=1)
    card_ids: list[str] = Field(min_length=1, max_length=10)


@router.get("/expeditions")
async def expeditions_overview(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await expeditions.overview(session, user)


@router.post("/expeditions", dependencies=[Depends(rate_limit(20, 60))])
async def start_expedition(
    body: ExpeditionStartBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await unlocks.require(session, user, "expeditions")
    return await expeditions.start(session, user, body.slot, body.duration_minutes, body.card_ids)


@router.post("/expeditions/{expedition_id}/claim", dependencies=[Depends(rate_limit(20, 60))])
async def claim_expedition(
    expedition_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await expeditions.claim(session, user, expedition_id)


class TapBody(BaseModel):
    count: int = Field(ge=0, le=1000)


@router.get("/workshop")
async def workshop_status(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await workshop.status(session, user)


@router.post("/workshop/taps", dependencies=[Depends(rate_limit(120, 60))])
async def workshop_taps(
    body: TapBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Lot de taps envoyé environ une fois par seconde par l'appli."""
    await unlocks.require(session, user, "workshop")
    return await workshop.tap(session, user, body.count)


class HigherLowerStartBody(BaseModel):
    resource_id: str
    stake: int = Field(ge=1)


class HigherLowerGuessBody(BaseModel):
    guess: str = Field(pattern="^(higher|lower)$")


@router.get("/higher-lower")
async def higher_lower_state(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await minigames.higher_lower_state(session, user)


@router.post("/higher-lower", dependencies=[Depends(rate_limit(30, 60))])
async def higher_lower_start(
    body: HigherLowerStartBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await unlocks.require(session, user, "higher_lower")
    return await minigames.higher_lower_start(session, user, body.resource_id, body.stake)


@router.post("/higher-lower/{game_id}/guess", dependencies=[Depends(rate_limit(60, 60))])
async def higher_lower_guess(
    game_id: int,
    body: HigherLowerGuessBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await minigames.higher_lower_guess(session, user, game_id, body.guess)


@router.post("/higher-lower/{game_id}/cashout", dependencies=[Depends(rate_limit(30, 60))])
async def higher_lower_cashout(
    game_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await minigames.higher_lower_cashout(session, user, game_id)


@router.get("/wheel")
async def wheel_state(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await minigames.wheel_state(session, user)


@router.post("/wheel/spin", dependencies=[Depends(rate_limit(20, 60))])
async def wheel_spin(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await unlocks.require(session, user, "wheel")
    return await minigames.wheel_spin(session, user)


class UpgradeBody(BaseModel):
    item: str = Field(pattern="^(booster|reroll)$")
    kind: str = Field(max_length=40)
    booster_id: str | None = None
    bonus_id: int | None = None
    token_id: int | None = None


class ConvertBody(BaseModel):
    from_id: str = Field(max_length=30)
    to_id: str = Field(max_length=30)
    amount: int = Field(ge=1, le=10_000_000)


@router.get("/machine")
async def machine_state(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await machine.machine_state(session, user)


@router.post("/machine/upgrade", dependencies=[Depends(rate_limit(30, 60))])
async def machine_upgrade(body: UpgradeBody, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    await unlocks.require(session, user, "machine")
    return await machine.upgrade(session, user, body.item, body.kind, body.booster_id, body.bonus_id, body.token_id)


@router.get("/converter")
async def converter_state(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await machine.converter_state(session, user)


@router.post("/converter", dependencies=[Depends(rate_limit(20, 60))])
async def convert(body: ConvertBody, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await unlocks.require(session, user, "converter")
    return await machine.convert(session, user, body.from_id, body.to_id, body.amount)


@admin_router.get("/config")
async def get_activities_config(session: AsyncSession = Depends(get_session)):
    return await activities_config.get_config(session)


@admin_router.put("/config")
async def put_activities_config(values: dict, session: AsyncSession = Depends(get_session)):
    return await activities_config.save_config(session, values)
