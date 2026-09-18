"""
Guildes : création, adhésion (ouverte / sur demande / sur invitation), rôles,
défi hebdomadaire, coffre (dons → XP + points), bonus temporaires, mur et
classements. Réglages dans activities_config (clé "guilds").
"""

import math
import random
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, func, select

from app.models.card import UserCard
from app.models.guild import (
    POLICY_INVITE, POLICY_OPEN, POLICY_REQUEST, ROLE_LEADER, ROLE_MEMBER, ROLE_OFFICER,
    Guild, GuildBuff, GuildContribution, GuildInvite, GuildMember, GuildMessage, GuildWeek,
)
from app.models.user import User
from app.services import activities_config
from app.services.quest_progress import weekly_key
from app.services.wallet import apply_delta, get_balance

POLICIES = (POLICY_OPEN, POLICY_REQUEST, POLICY_INVITE)
MANAGERS = (ROLE_LEADER, ROLE_OFFICER)
DONATION_RESOURCES = ("coins", "dust")


# ─────────────────────────────  OUTILS  ─────────────────────────────

async def _cfg(session: AsyncSession) -> dict:
    return (await activities_config.get_config(session))["guilds"]


def level_for_xp(xp: int, cfg: dict) -> int:
    """Niveau L atteint quand xp ≥ xp_per_level × L(L−1)/2 (paliers de plus en plus longs)."""
    step = cfg["xp_per_level"]
    level = 1
    while step * (level + 1) * level // 2 <= xp:
        level += 1
    return level


def xp_for_level(level: int, cfg: dict) -> int:
    return cfg["xp_per_level"] * level * (level - 1) // 2


def max_members(level: int, cfg: dict) -> int:
    size = cfg["base_members"]
    for threshold, members in cfg["members_by_level"].items():
        if level >= int(threshold):
            size = max(size, members)
    return size


async def membership(session: AsyncSession, user_id: int) -> GuildMember | None:
    return await session.get(GuildMember, user_id)


async def _require_member(session: AsyncSession, user: User, roles=None) -> tuple[Guild, GuildMember]:
    member = await membership(session, user.id)
    if not member:
        raise HTTPException(404, "Tu n'es dans aucune guilde.")
    if roles and member.role not in roles:
        raise HTTPException(403, "Action réservée au chef ou aux officiers.")
    guild = await session.get(Guild, member.guild_id)
    return guild, member


async def _members(session: AsyncSession, guild_id: int) -> list[GuildMember]:
    return list((await session.execute(
        select(GuildMember).where(GuildMember.guild_id == guild_id).order_by(GuildMember.joined_at)
    )).scalars().all())


async def _system_message(session: AsyncSession, guild_id: int, body: str) -> None:
    session.add(GuildMessage(guild_id=guild_id, user_id=None, body=body[:300]))


async def active_buffs(session: AsyncSession, guild_id: int) -> list[GuildBuff]:
    return list((await session.execute(
        select(GuildBuff).where(GuildBuff.guild_id == guild_id, GuildBuff.expires_at > datetime.utcnow())
    )).scalars().all())


async def buff_value(session: AsyncSession, user_id: int, kind: str) -> float | None:
    """Valeur d'un bonus de guilde actif pour ce joueur (None si aucun)."""
    member = await membership(session, user_id)
    if not member:
        return None
    buffs = [b for b in await active_buffs(session, member.guild_id) if b.kind == kind]
    if not buffs:
        return None
    return (await _cfg(session))["buffs"][kind]["value"]


async def level_perks(session: AsyncSession, user_id: int) -> dict:
    """Bonus permanents liés au niveau de la guilde du joueur."""
    member = await membership(session, user_id)
    if not member:
        return {"daily_bonus_pct": 0, "extra_expedition_slots": 0}
    cfg = await _cfg(session)
    guild = await session.get(Guild, member.guild_id)
    level = level_for_xp(guild.xp, cfg)
    return {
        "daily_bonus_pct": min(cfg["daily_bonus_cap_pct"], cfg["daily_bonus_per_level_pct"] * (level - 1)),
        "extra_expedition_slots": 1 if level >= cfg["expedition_slot_level"] else 0,
    }


# ─────────────────────────────  CRÉATION ET ADHÉSION  ─────────────────────────────

async def _check_cooldown(session: AsyncSession, user: User) -> None:
    cfg = await _cfg(session)
    if user.guild_left_at:
        ready = user.guild_left_at + timedelta(hours=cfg["leave_cooldown_hours"])
        if datetime.utcnow() < ready:
            minutes = int((ready - datetime.utcnow()).total_seconds() // 60) + 1
            raise HTTPException(400, f"Tu as quitté une guilde récemment : encore {minutes} min avant d'en rejoindre une.")


async def _add_member(session: AsyncSession, guild: Guild, user: User, role: str = ROLE_MEMBER) -> None:
    cfg = await _cfg(session)
    if await membership(session, user.id):
        raise HTTPException(409, "Tu es déjà dans une guilde.")
    count = len(await _members(session, guild.id))
    if count >= max_members(level_for_xp(guild.xp, cfg), cfg):
        raise HTTPException(409, "Cette guilde est complète.")
    session.add(GuildMember(user_id=user.id, guild_id=guild.id, role=role))
    await session.execute(delete(GuildInvite).where(GuildInvite.user_id == user.id))
    await _system_message(session, guild.id, f"{user.display_name} a rejoint la guilde.")


def _clean_tag(tag: str) -> str:
    tag = (tag or "").strip().upper()
    if not (2 <= len(tag) <= 4 and tag.isalnum()):
        raise HTTPException(400, "Le tag doit faire 2 à 4 lettres ou chiffres.")
    return tag


async def create(session: AsyncSession, user: User, name: str, tag: str, icon: str, color: str, policy: str) -> Guild:
    cfg = await _cfg(session)
    await _check_cooldown(session, user)
    if await membership(session, user.id):
        raise HTTPException(409, "Quitte ta guilde actuelle avant d'en créer une.")
    name = (name or "").strip()
    if not 3 <= len(name) <= 24:
        raise HTTPException(400, "Le nom doit faire entre 3 et 24 caractères.")
    tag = _clean_tag(tag)
    if policy not in POLICIES:
        raise HTTPException(400, "Mode d'adhésion invalide.")
    if (await session.execute(select(Guild.id).where(func.lower(Guild.name) == name.lower()))).first():
        raise HTTPException(409, "Ce nom de guilde est déjà pris.")
    if (await session.execute(select(Guild.id).where(Guild.tag == tag))).first():
        raise HTTPException(409, "Ce tag est déjà pris.")
    if user.coins < cfg["creation_cost"]:
        raise HTTPException(400, f"Créer une guilde coûte {cfg['creation_cost']} pièces.")

    await apply_delta(session, user, "coins", -cfg["creation_cost"])
    guild = Guild(name=name, tag=tag, icon=(icon or "🛡️")[:8], color=(color or "#6366f1")[:9], join_policy=policy)
    session.add(guild)
    await session.flush()
    session.add(GuildMember(user_id=user.id, guild_id=guild.id, role=ROLE_LEADER))
    await session.execute(delete(GuildInvite).where(GuildInvite.user_id == user.id))
    await _system_message(session, guild.id, f"{user.display_name} a fondé la guilde.")
    await session.commit()
    await session.refresh(guild)
    return guild


async def join(session: AsyncSession, user: User, guild_id: int) -> str:
    """Rejoint (guilde ouverte) ou demande à rejoindre. Retourne "joined" ou "requested"."""
    guild = await session.get(Guild, guild_id)
    if not guild:
        raise HTTPException(404, "Guilde introuvable.")
    await _check_cooldown(session, user)
    if await membership(session, user.id):
        raise HTTPException(409, "Tu es déjà dans une guilde.")

    invite = (await session.execute(select(GuildInvite).where(
        GuildInvite.guild_id == guild_id, GuildInvite.user_id == user.id, GuildInvite.kind == "invite",
    ))).scalars().first()
    if guild.join_policy == POLICY_OPEN or invite:
        await _add_member(session, guild, user)
        await session.commit()
        return "joined"
    if guild.join_policy == POLICY_INVITE:
        raise HTTPException(403, "Cette guilde est sur invitation uniquement.")
    already = (await session.execute(select(GuildInvite.id).where(
        GuildInvite.guild_id == guild_id, GuildInvite.user_id == user.id, GuildInvite.kind == "request",
    ))).first()
    if not already:
        session.add(GuildInvite(guild_id=guild_id, user_id=user.id, kind="request"))
        await session.commit()
    return "requested"


async def invite(session: AsyncSession, user: User, username: str) -> None:
    guild, _ = await _require_member(session, user, MANAGERS)
    target = (await session.execute(select(User).where(User.username == username.strip().lower()))).scalar_one_or_none()
    if not target:
        raise HTTPException(404, "Aucun joueur avec ce pseudo.")
    if await membership(session, target.id):
        raise HTTPException(409, "Ce joueur est déjà dans une guilde.")
    exists = (await session.execute(select(GuildInvite.id).where(
        GuildInvite.guild_id == guild.id, GuildInvite.user_id == target.id, GuildInvite.kind == "invite",
    ))).first()
    if not exists:
        session.add(GuildInvite(guild_id=guild.id, user_id=target.id, kind="invite"))
        await session.commit()


async def answer_request(session: AsyncSession, user: User, invite_id: int, accept: bool) -> None:
    guild, _ = await _require_member(session, user, MANAGERS)
    req = await session.get(GuildInvite, invite_id)
    if not req or req.guild_id != guild.id or req.kind != "request":
        raise HTTPException(404, "Demande introuvable.")
    await session.delete(req)
    if accept:
        applicant = await session.get(User, req.user_id)
        await _check_cooldown(session, applicant)
        await _add_member(session, guild, applicant)
    await session.commit()


async def answer_invite(session: AsyncSession, user: User, invite_id: int, accept: bool) -> None:
    inv = await session.get(GuildInvite, invite_id)
    if not inv or inv.user_id != user.id or inv.kind != "invite":
        raise HTTPException(404, "Invitation introuvable.")
    if accept:
        await join(session, user, inv.guild_id)
    else:
        await session.delete(inv)
        await session.commit()


async def _promote_successor(session: AsyncSession, guild: Guild) -> None:
    """Le chef est parti : le plus ancien officier, sinon le plus ancien membre, prend la tête."""
    members = await _members(session, guild.id)
    if not members:
        return
    successor = next((m for m in members if m.role == ROLE_OFFICER), members[0])
    successor.role = ROLE_LEADER
    session.add(successor)
    heir = await session.get(User, successor.user_id)
    await _system_message(session, guild.id, f"{heir.display_name if heir else 'Un membre'} devient chef de guilde.")


async def _dissolve(session: AsyncSession, guild: Guild) -> None:
    for model in (GuildContribution, GuildWeek, GuildBuff, GuildMessage, GuildInvite, GuildMember):
        await session.execute(delete(model).where(model.guild_id == guild.id))
    await session.delete(guild)


async def leave(session: AsyncSession, user: User) -> None:
    guild, member = await _require_member(session, user)
    was_leader = member.role == ROLE_LEADER
    await session.delete(member)
    await session.flush()
    user.guild_left_at = datetime.utcnow()
    session.add(user)
    if not await _members(session, guild.id):
        await _dissolve(session, guild)
    else:
        await _system_message(session, guild.id, f"{user.display_name} a quitté la guilde.")
        if was_leader:
            await _promote_successor(session, guild)
    await session.commit()


async def kick(session: AsyncSession, user: User, target_id: int) -> None:
    guild, me = await _require_member(session, user, MANAGERS)
    target = await session.get(GuildMember, target_id)
    if not target or target.guild_id != guild.id or target_id == user.id:
        raise HTTPException(404, "Membre introuvable.")
    if target.role == ROLE_LEADER or (me.role == ROLE_OFFICER and target.role == ROLE_OFFICER):
        raise HTTPException(403, "Tu ne peux pas exclure ce membre.")
    await session.delete(target)
    kicked = await session.get(User, target_id)
    if kicked:
        kicked.guild_left_at = datetime.utcnow()
        session.add(kicked)
        await _system_message(session, guild.id, f"{kicked.display_name} a été exclu de la guilde.")
    await session.commit()


async def set_role(session: AsyncSession, user: User, target_id: int, role: str) -> None:
    """Chef uniquement : promouvoir officier, rétrograder, ou passer la main (role="leader")."""
    guild, me = await _require_member(session, user, (ROLE_LEADER,))
    target = await session.get(GuildMember, target_id)
    if not target or target.guild_id != guild.id or target_id == user.id:
        raise HTTPException(404, "Membre introuvable.")
    if role not in (ROLE_LEADER, ROLE_OFFICER, ROLE_MEMBER):
        raise HTTPException(400, "Rôle invalide.")
    target.role = role
    if role == ROLE_LEADER:
        me.role = ROLE_OFFICER
        session.add(me)
        new_leader = await session.get(User, target_id)
        await _system_message(session, guild.id, f"{new_leader.display_name} devient chef de guilde.")
    session.add(target)
    await session.commit()


async def update_settings(session: AsyncSession, user: User, data: dict) -> Guild:
    guild, me = await _require_member(session, user, MANAGERS)
    if "welcome_message" in data:
        guild.welcome_message = (data["welcome_message"] or "")[:300]
    if me.role == ROLE_LEADER:
        if data.get("join_policy") in POLICIES:
            guild.join_policy = data["join_policy"]
        if data.get("icon"):
            guild.icon = data["icon"][:8]
        if data.get("color"):
            guild.color = data["color"][:9]
    session.add(guild)
    await session.commit()
    return guild


# ─────────────────────────────  DÉFI HEBDOMADAIRE  ─────────────────────────────

def _target(metric_cfg: float, members: int, tier: int, cfg: dict) -> int:
    return max(1, math.ceil(metric_cfg * max(1, members) * (1 + cfg["tier_step"] * (tier - 1))))


async def current_week(session: AsyncSession, guild: Guild) -> GuildWeek:
    """Défi de la semaine en cours ; à la première consultation d'une nouvelle
    semaine, évalue la précédente (palier +1 si les 3 objectifs sont réussis,
    sinon retour à la moitié) et tire 3 nouveaux objectifs."""
    key = weekly_key()
    week = await session.get(GuildWeek, (guild.id, key))
    if week:
        return week
    cfg = await _cfg(session)
    previous = (await session.execute(
        select(GuildWeek).where(GuildWeek.guild_id == guild.id).order_by(GuildWeek.week_key.desc())
    )).scalars().first()
    if previous:
        if all(o.get("completed_at") for o in previous.objectives):
            guild.challenge_tier = previous.tier + 1
        else:
            guild.challenge_tier = max(1, previous.tier // 2)
        guild.challenge_best_tier = max(guild.challenge_best_tier, guild.challenge_tier)
        session.add(guild)
    members = len(await _members(session, guild.id))
    metrics = random.sample(list(cfg["objectives"].keys()), k=min(3, len(cfg["objectives"])))
    week = GuildWeek(guild_id=guild.id, week_key=key, tier=guild.challenge_tier, objectives=[
        {"metric": m, "target": _target(cfg["objectives"][m], members, guild.challenge_tier, cfg),
         "progress": 0, "completed_at": None}
        for m in metrics
    ])
    session.add(week)
    await session.flush()
    return week


async def track(session: AsyncSession, user_id: int, metric: str, amount: int) -> None:
    """Appelé à chaque action comptée (cf. quest_progress.increment). Ne commit pas."""
    member = await membership(session, user_id)
    if not member:
        return
    cfg = await _cfg(session)
    if metric not in cfg["objectives"]:
        return
    guild = await session.get(Guild, member.guild_id)
    week = await current_week(session, guild)
    objectives = [dict(o) for o in week.objectives]
    objective = next((o for o in objectives if o["metric"] == metric), None)
    if not objective:
        return
    objective["progress"] = objective["progress"] + amount
    contribution = await session.get(GuildContribution, (guild.id, week.week_key, metric, user_id))
    if not contribution:
        contribution = GuildContribution(guild_id=guild.id, week_key=week.week_key, metric=metric, user_id=user_id)
    contribution.count += amount
    session.add(contribution)
    if not objective["completed_at"] and objective["progress"] >= objective["target"]:
        objective["completed_at"] = datetime.utcnow().isoformat()
        guild.xp += cfg["objective_xp"] * week.tier
        session.add(guild)
        await _system_message(session, guild.id, f"Objectif atteint : {cfg['objective_labels'].get(metric, metric)} !")
    week.objectives = objectives  # réaffectation : la colonne JSON doit être réenregistrée
    session.add(week)


async def claim_objective(session: AsyncSession, user: User, metric: str) -> dict:
    guild, _ = await _require_member(session, user)
    cfg = await _cfg(session)
    week = await current_week(session, guild)
    objective = next((o for o in week.objectives if o["metric"] == metric), None)
    if not objective or not objective["completed_at"]:
        raise HTTPException(400, "Cet objectif n'est pas encore atteint.")
    contribution = await session.get(GuildContribution, (guild.id, week.week_key, metric, user.id))
    if not contribution or contribution.count <= 0:
        raise HTTPException(403, "Il faut avoir contribué à cet objectif pour en récupérer la récompense.")
    if contribution.claimed_at:
        raise HTTPException(409, "Récompense déjà récupérée.")
    reward = {"coins": cfg["objective_coins"] * week.tier, "dust": cfg["objective_dust"] * week.tier}
    await apply_delta(session, user, "coins", reward["coins"])
    await apply_delta(session, user, "dust", reward["dust"])
    contribution.claimed_at = datetime.utcnow()
    session.add(contribution)
    await session.commit()
    return reward


# ─────────────────────────────  COFFRE ET BONUS  ─────────────────────────────

async def donate(session: AsyncSession, user: User, resource_id: str, amount: int) -> dict:
    guild, member = await _require_member(session, user)
    cfg = await _cfg(session)
    if resource_id not in DONATION_RESOURCES:
        raise HTTPException(400, "Dons en pièces ou en poussière uniquement.")
    rate = cfg["points_per_coins"] if resource_id == "coins" else cfg["points_per_dust"]
    points = amount // rate
    if points < 1:
        raise HTTPException(400, f"Don minimum : {rate} {'pièces' if resource_id == 'coins' else 'poussière'}.")
    amount = points * rate  # on ne prend que la part convertie en points
    if await get_balance(session, user, resource_id) < amount:
        raise HTTPException(400, "Solde insuffisant.")
    await apply_delta(session, user, resource_id, -amount)
    guild.chest_points += points
    guild.chest_total += points
    guild.xp += points
    member.donated_points += points
    session.add_all([guild, member])
    await session.commit()
    return {"points": points, "spent": amount}


async def buy_buff(session: AsyncSession, user: User, kind: str) -> GuildBuff:
    guild, _ = await _require_member(session, user, MANAGERS)
    cfg = await _cfg(session)
    buff_cfg = cfg["buffs"].get(kind)
    if not buff_cfg:
        raise HTTPException(404, "Bonus inconnu.")
    if guild.chest_points < buff_cfg["cost"]:
        raise HTTPException(400, f"Il faut {buff_cfg['cost']} points dans le coffre.")
    now = datetime.utcnow()
    current = next((b for b in await active_buffs(session, guild.id) if b.kind == kind), None)
    # Racheter un bonus actif prolonge sa durée.
    start = current.expires_at if current else now
    guild.chest_points -= buff_cfg["cost"]
    buff = current or GuildBuff(guild_id=guild.id, kind=kind, expires_at=now, bought_by=user.id)
    buff.expires_at = start + timedelta(hours=buff_cfg["hours"])
    session.add_all([guild, buff])
    await _system_message(session, guild.id, f"{user.display_name} a activé « {buff_cfg['label']} ».")
    await session.commit()
    await session.refresh(buff)
    return buff


# ─────────────────────────────  MUR  ─────────────────────────────

async def post_message(session: AsyncSession, user: User, body: str) -> None:
    guild, _ = await _require_member(session, user)
    body = (body or "").strip()
    if not 1 <= len(body) <= 200:
        raise HTTPException(400, "Message de 1 à 200 caractères.")
    session.add(GuildMessage(guild_id=guild.id, user_id=user.id, body=body))
    await session.commit()


async def wall(session: AsyncSession, guild_id: int) -> list[dict]:
    rows = (await session.execute(
        select(GuildMessage, User.display_name)
        .join(User, User.id == GuildMessage.user_id, isouter=True)
        .where(GuildMessage.guild_id == guild_id)
        .order_by(GuildMessage.created_at.desc()).limit(50)
    )).all()
    return [
        {"id": m.id, "user_id": m.user_id, "author": name, "body": m.body, "created_at": m.created_at, "system": m.user_id is None}
        for m, name in reversed(rows)
    ]


# ─────────────────────────────  VUES ET CLASSEMENTS  ─────────────────────────────

async def _power_by_guild(session: AsyncSession) -> dict[int, int]:
    rows = (await session.execute(
        select(GuildMember.guild_id, func.coalesce(func.sum(UserCard.power), 0))
        .join(UserCard, UserCard.user_id == GuildMember.user_id, isouter=True)
        .group_by(GuildMember.guild_id)
    )).all()
    return {gid: int(total or 0) for gid, total in rows}


async def summary(session: AsyncSession, guild: Guild, power: int | None = None) -> dict:
    cfg = await _cfg(session)
    level = level_for_xp(guild.xp, cfg)
    count = len(await _members(session, guild.id))
    if power is None:
        power = (await _power_by_guild(session)).get(guild.id, 0)
    return {
        "id": guild.id, "name": guild.name, "tag": guild.tag, "icon": guild.icon, "color": guild.color,
        "join_policy": guild.join_policy, "level": level, "members": count,
        "max_members": max_members(level, cfg), "power": power, "chest_total": guild.chest_total,
        "challenge_best_tier": guild.challenge_best_tier,
    }


async def detail(session: AsyncSession, user: User) -> dict | None:
    """Vue complète de la guilde du joueur."""
    member = await membership(session, user.id)
    if not member:
        return None
    cfg = await _cfg(session)
    guild = await session.get(Guild, member.guild_id)
    week = await current_week(session, guild)
    await session.commit()
    level = level_for_xp(guild.xp, cfg)

    members = []
    for m in await _members(session, guild.id):
        u = await session.get(User, m.user_id)
        if u:
            members.append({"user_id": u.id, "username": u.username, "display_name": u.display_name,
                            "role": m.role, "joined_at": m.joined_at, "donated_points": m.donated_points})
    order = {ROLE_LEADER: 0, ROLE_OFFICER: 1, ROLE_MEMBER: 2}
    members.sort(key=lambda x: (order[x["role"]], -x["donated_points"]))

    contributions = {
        c.metric: c for c in (await session.execute(select(GuildContribution).where(
            GuildContribution.guild_id == guild.id, GuildContribution.week_key == week.week_key,
            GuildContribution.user_id == user.id,
        ))).scalars().all()
    }
    objectives = []
    for o in week.objectives:
        mine = contributions.get(o["metric"])
        objectives.append({
            **o, "label": cfg["objective_labels"].get(o["metric"], o["metric"]),
            "my_contribution": mine.count if mine else 0,
            "claimable": bool(o["completed_at"] and mine and mine.count > 0 and not mine.claimed_at),
            "claimed": bool(mine and mine.claimed_at),
            "reward_coins": cfg["objective_coins"] * week.tier, "reward_dust": cfg["objective_dust"] * week.tier,
        })

    requests = []
    if member.role in MANAGERS:
        for req in (await session.execute(select(GuildInvite).where(
            GuildInvite.guild_id == guild.id, GuildInvite.kind == "request",
        ))).scalars().all():
            applicant = await session.get(User, req.user_id)
            if applicant:
                requests.append({"id": req.id, "user_id": applicant.id, "display_name": applicant.display_name,
                                 "username": applicant.username})

    buffs = [{"kind": b.kind, "label": cfg["buffs"][b.kind]["label"], "expires_at": b.expires_at}
             for b in await active_buffs(session, guild.id) if b.kind in cfg["buffs"]]
    return {
        **(await summary(session, guild)),
        "my_role": member.role, "welcome_message": guild.welcome_message,
        "xp": guild.xp, "xp_current_level": xp_for_level(level, cfg), "xp_next_level": xp_for_level(level + 1, cfg),
        "chest_points": guild.chest_points, "challenge_tier": week.tier,
        "objectives": objectives, "week_key": week.week_key, "members_list": members, "requests": requests,
        "buffs": buffs,
        "shop": [{"kind": k, "label": v["label"], "cost": v["cost"], "hours": v["hours"]} for k, v in cfg["buffs"].items()],
        "perks": {
            "daily_bonus_pct": min(cfg["daily_bonus_cap_pct"], cfg["daily_bonus_per_level_pct"] * (level - 1)),
            "extra_expedition_slots": 1 if level >= cfg["expedition_slot_level"] else 0,
            "expedition_slot_level": cfg["expedition_slot_level"],
        },
        "points_per_coins": cfg["points_per_coins"], "points_per_dust": cfg["points_per_dust"],
    }


async def my_invites(session: AsyncSession, user: User) -> list[dict]:
    rows = (await session.execute(select(GuildInvite).where(
        GuildInvite.user_id == user.id, GuildInvite.kind == "invite",
    ))).scalars().all()
    out = []
    for inv in rows:
        guild = await session.get(Guild, inv.guild_id)
        if guild:
            out.append({"id": inv.id, "guild": await summary(session, guild)})
    return out


async def search(session: AsyncSession, query: str) -> list[dict]:
    stmt = select(Guild)
    if query:
        like = f"%{query.strip().lower()}%"
        stmt = stmt.where(func.lower(Guild.name).like(like) | func.lower(Guild.tag).like(like))
    guilds = (await session.execute(stmt.limit(30))).scalars().all()
    powers = await _power_by_guild(session)
    return [await summary(session, g, powers.get(g.id, 0)) for g in guilds]


RANKING_KINDS = ("overall", "level", "power", "chest", "challenge")


async def rankings(session: AsyncSession, kind: str) -> list[dict]:
    if kind not in RANKING_KINDS:
        raise HTTPException(400, "Classement inconnu.")
    guilds = (await session.execute(select(Guild))).scalars().all()
    powers = await _power_by_guild(session)
    rows = [await summary(session, g, powers.get(g.id, 0)) for g in guilds]
    for r, g in zip(rows, guilds):
        r["xp"] = g.xp

    def ranks(key) -> dict[int, int]:
        ordered = sorted(rows, key=key, reverse=True)
        return {r["id"]: i + 1 for i, r in enumerate(ordered)}

    by_level = ranks(lambda r: (r["level"], r["xp"]))
    by_power = ranks(lambda r: r["power"])
    by_chest = ranks(lambda r: r["chest_total"])
    for r in rows:
        r["average_rank"] = round((by_level[r["id"]] + by_power[r["id"]] + by_chest[r["id"]]) / 3, 2)

    sort_key = {
        "level": lambda r: (-r["level"], -r["xp"]),
        "power": lambda r: -r["power"],
        "chest": lambda r: -r["chest_total"],
        "challenge": lambda r: -r["challenge_best_tier"],
        "overall": lambda r: r["average_rank"],
    }[kind]
    rows.sort(key=sort_key)
    return [{**r, "rank": i + 1} for i, r in enumerate(rows[:100])]


async def tags_for(session: AsyncSession, user_ids: list[int]) -> dict[int, dict]:
    """Étiquette de guilde (id, tag, couleur, icône) de chaque joueur qui en a une."""
    if not user_ids:
        return {}
    rows = (await session.execute(
        select(GuildMember.user_id, Guild)
        .join(Guild, Guild.id == GuildMember.guild_id)
        .where(GuildMember.user_id.in_(user_ids))
    )).all()
    return {uid: {"id": g.id, "tag": g.tag, "color": g.color, "icon": g.icon} for uid, g in rows}
