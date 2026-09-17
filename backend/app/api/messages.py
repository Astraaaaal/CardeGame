"""
Routes — messagerie (inbox joueur, cadeaux) et diffusion admin.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import get_current_user, require_admin
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.schemas.message import MessageOut, SendGiftBody, SendAdminMessageBody, SendAdminMessageResponse
from app.services import messages as svc
from app.services.ranking import refresh_all_best_ranks

router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/", response_model=list[MessageOut])
async def list_messages(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await svc.list_inbox(session, user.id)
    return [await svc.build_out(session, m) for m in rows]


@router.get("/unread-count")
async def get_unread_count(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return {"count": await svc.unread_count(session, user.id)}


@router.post("/{message_id}/read", response_model=MessageOut)
async def read_message(
    message_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg = await svc.get_message_or_404(session, message_id, user.id)
    msg = await svc.mark_read(session, msg)
    return await svc.build_out(session, msg)


@router.post("/{message_id}/claim", response_model=MessageOut)
async def claim_message(
    message_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg = await svc.get_message_or_404(session, message_id, user.id)
    msg = await svc.claim(session, msg)
    if msg.reward_card_id and msg.claimed_at:
        await refresh_all_best_ranks(session)
        await session.commit()
    return await svc.build_out(session, msg)


@router.delete("/{message_id}", status_code=204)
async def remove_message(
    message_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg = await svc.get_message_or_404(session, message_id, user.id)
    await svc.delete_message(session, msg)


@router.post(
    "/gift", response_model=MessageOut, status_code=201,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def send_gift(
    body: SendGiftBody,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    msg = await svc.send_gift(
        session, user, body.username, body.subject, body.body,
        body.item_type, body.user_card_id, body.resource_id, body.amount,
        body.booster_id, body.bonus_id, body.reroll_token_id,
    )
    return await svc.build_out(session, msg)


@admin_router.post("/", response_model=SendAdminMessageResponse)
async def send_admin_message(
    body: SendAdminMessageBody,
    session: AsyncSession = Depends(get_session),
):
    count = await svc.send_admin_broadcast(
        session, body.usernames, body.subject, body.body,
        body.reward_resource_id, body.reward_amount,
    )
    return SendAdminMessageResponse(sent_count=count)
