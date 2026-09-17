"""
Routes — session d'échange en direct.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.schemas.trade_session import (
    TradeSessionOut, AddCardItemBody, AddResourceItemBody, SetReadyBody,
    AddBoosterItemBody, AddRerollItemBody,
)
from app.services import trade_session as svc
from app.services.ranking import refresh_all_best_ranks

router = APIRouter()


@router.get("/{session_id}", response_model=TradeSessionOut)
async def get_trade_session(
    session_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    return await svc.build_out(session, trade, user.id)


@router.post(
    "/{session_id}/items/cards", response_model=TradeSessionOut,
    dependencies=[Depends(rate_limit(60, 60))],
)
async def add_card(
    session_id: int,
    body: AddCardItemBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.add_card_item(session, trade, user.id, body.user_card_id)
    return await svc.build_out(session, trade, user.id)


@router.post(
    "/{session_id}/items/resources", response_model=TradeSessionOut,
    dependencies=[Depends(rate_limit(60, 60))],
)
async def add_resource(
    session_id: int,
    body: AddResourceItemBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.add_resource_item(session, trade, user.id, body.resource_id, body.amount)
    return await svc.build_out(session, trade, user.id)


@router.post(
    "/{session_id}/items/boosters", response_model=TradeSessionOut,
    dependencies=[Depends(rate_limit(60, 60))],
)
async def add_booster(
    session_id: int,
    body: AddBoosterItemBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.add_booster_item(session, trade, user.id, body.booster_id, body.bonus_id, body.amount)
    return await svc.build_out(session, trade, user.id)


@router.post(
    "/{session_id}/items/rerolls", response_model=TradeSessionOut,
    dependencies=[Depends(rate_limit(60, 60))],
)
async def add_reroll(
    session_id: int,
    body: AddRerollItemBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.add_reroll_item(session, trade, user.id, body.reroll_token_id, body.amount)
    return await svc.build_out(session, trade, user.id)


@router.delete("/{session_id}/items/{item_id}", response_model=TradeSessionOut)
async def remove_item(
    session_id: int,
    item_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.remove_item(session, trade, user.id, item_id)
    return await svc.build_out(session, trade, user.id)


@router.post("/{session_id}/ready", response_model=TradeSessionOut)
async def set_ready(
    session_id: int,
    body: SetReadyBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.set_ready(session, trade, user.id, body.ready)
    return await svc.build_out(session, trade, user.id)


@router.post("/{session_id}/confirm", response_model=TradeSessionOut)
async def confirm_trade(
    session_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    removed = await svc.confirm(session, trade, user.id)
    if trade.status == svc.STATUS_COMPLETED:
        await refresh_all_best_ranks(session)
        await session.commit()
    return await svc.build_out(session, trade, user.id, removed_items=removed)


@router.post("/{session_id}/cancel", status_code=204)
async def cancel_trade(
    session_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    trade = await svc.get_session_or_404(session, session_id, user.id)
    await svc.cancel(session, trade, user.id)
