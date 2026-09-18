"""
Routes — guildes : création, adhésion, rôles, défi hebdomadaire, coffre,
bonus, mur et classements.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.database import get_session
from app.models.guild import Guild
from app.models.user import User
from app.services import guilds

router = APIRouter()


class CreateGuildBody(BaseModel):
    name: str = Field(min_length=3, max_length=24)
    tag: str = Field(min_length=2, max_length=4)
    icon: str = Field(default="🛡️", max_length=8)
    color: str = Field(default="#6366f1", max_length=9)
    join_policy: str = Field(default="request", pattern="^(open|request|invite)$")


class GuildSettingsBody(BaseModel):
    welcome_message: str | None = Field(default=None, max_length=300)
    join_policy: str | None = Field(default=None, pattern="^(open|request|invite)$")
    icon: str | None = Field(default=None, max_length=8)
    color: str | None = Field(default=None, max_length=9)


class UsernameBody(BaseModel):
    username: str = Field(min_length=1, max_length=40)


class AnswerBody(BaseModel):
    accept: bool


class RoleBody(BaseModel):
    role: str = Field(pattern="^(leader|officer|member)$")


class DonateBody(BaseModel):
    resource_id: str
    amount: int = Field(ge=1, le=10_000_000)


class WallBody(BaseModel):
    body: str = Field(min_length=1, max_length=200)


@router.get("/me")
async def my_guild(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Ma guilde (détail complet) ou null, avec les invitations reçues."""
    return {
        "guild": await guilds.detail(session, user),
        "invites": await guilds.my_invites(session, user),
        "left_at": user.guild_left_at,
        "cooldown_hours": (await guilds._cfg(session))["leave_cooldown_hours"],
        "creation_cost": (await guilds._cfg(session))["creation_cost"],
    }


@router.get("/search")
async def search_guilds(q: str = "", _user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await guilds.search(session, q)


@router.get("/rankings")
async def guild_rankings(kind: str = "overall", _user: User = Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)):
    return await guilds.rankings(session, kind)


@router.post("", dependencies=[Depends(rate_limit(5, 60))])
async def create_guild(body: CreateGuildBody, user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    guild = await guilds.create(session, user, body.name, body.tag, body.icon, body.color, body.join_policy)
    return await guilds.summary(session, guild)


@router.post("/{guild_id}/join", dependencies=[Depends(rate_limit(10, 60))])
async def join_guild(guild_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return {"result": await guilds.join(session, user, guild_id)}


@router.post("/leave")
async def leave_guild(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await guilds.leave(session, user)
    return {"ok": True}


@router.patch("/settings")
async def update_guild_settings(body: GuildSettingsBody, user: User = Depends(get_current_user),
                                session: AsyncSession = Depends(get_session)):
    await guilds.update_settings(session, user, body.model_dump(exclude_unset=True))
    return await guilds.detail(session, user)


@router.post("/invites", dependencies=[Depends(rate_limit(20, 60))])
async def invite_player(body: UsernameBody, user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    await guilds.invite(session, user, body.username)
    return {"ok": True}


@router.post("/invites/{invite_id}/answer")
async def answer_invite(invite_id: int, body: AnswerBody, user: User = Depends(get_current_user),
                        session: AsyncSession = Depends(get_session)):
    await guilds.answer_invite(session, user, invite_id, body.accept)
    return {"ok": True}


@router.post("/requests/{request_id}/answer")
async def answer_request(request_id: int, body: AnswerBody, user: User = Depends(get_current_user),
                         session: AsyncSession = Depends(get_session)):
    await guilds.answer_request(session, user, request_id, body.accept)
    return await guilds.detail(session, user)


@router.post("/members/{member_id}/role")
async def set_member_role(member_id: int, body: RoleBody, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    await guilds.set_role(session, user, member_id, body.role)
    return await guilds.detail(session, user)


@router.post("/members/{member_id}/kick")
async def kick_member(member_id: int, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await guilds.kick(session, user, member_id)
    return await guilds.detail(session, user)


@router.post("/objectives/{metric}/claim", dependencies=[Depends(rate_limit(20, 60))])
async def claim_objective(metric: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await guilds.claim_objective(session, user, metric)


@router.post("/donate", dependencies=[Depends(rate_limit(20, 60))])
async def donate(body: DonateBody, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await guilds.donate(session, user, body.resource_id, body.amount)


@router.post("/buffs/{kind}", dependencies=[Depends(rate_limit(10, 60))])
async def buy_buff(kind: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await guilds.buy_buff(session, user, kind)
    return await guilds.detail(session, user)


@router.get("/wall")
async def guild_wall(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    guild, _ = await guilds._require_member(session, user)
    return await guilds.wall(session, guild.id)


@router.post("/wall", dependencies=[Depends(rate_limit(20, 60))])
async def post_on_wall(body: WallBody, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    await guilds.post_message(session, user, body.body)
    guild, _ = await guilds._require_member(session, user)
    return await guilds.wall(session, guild.id)


@router.get("/{guild_id}")
async def guild_public(guild_id: int, _user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    guild = await session.get(Guild, guild_id)
    if not guild:
        raise HTTPException(404, "Guilde introuvable.")
    return {**(await guilds.summary(session, guild)), "welcome_message": guild.welcome_message}
