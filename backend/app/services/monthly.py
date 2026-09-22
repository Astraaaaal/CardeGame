"""
Défi du mois : chaque mois, la puissance des cartes OBTENUES pendant le mois
(boosters, récompenses, boutique, expéditions) fait gagner des points — pas les
cartes reçues par échange ou cadeau, et recycler ne retire rien. Classement solo
et par guilde (somme des points gagnés par ses membres pendant qu'ils y étaient).

Au premier passage après la fin d'un mois, il est clôturé : récompenses par
tranches de rang envoyées par la messagerie, champions retenus (badge affiché
le mois suivant). Réglages : section « monthly » des activités.
"""

import math
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.guild import Guild, GuildMember
from app.models.message import Message
from app.models.monthly import GuildMonthlyScore, MonthlyResult, MonthlyScore
from app.models.user import User
from app.services import activities_config, message_rewards

MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
          "septembre", "octobre", "novembre", "décembre"]
_FINALIZE_LOCK_SPACE = 2


def month_key(now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    return f"{now.year:04d}-{now.month:02d}"


def month_label(key: str) -> str:
    year, month = key.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def month_end(key: str) -> datetime:
    year, month = map(int, key.split("-"))
    return datetime(year + (month == 12), month % 12 + 1, 1)


async def _add(session: AsyncSession, model, keys: dict, points: int) -> None:
    """Ajout atomique (ligne créée au besoin) : pas de points perdus entre actions simultanées."""
    table = model.__table__
    dialect = postgresql if session.bind.dialect.name == "postgresql" else sqlite
    await session.execute(
        dialect.insert(table).values(**keys, points=points)
        .on_conflict_do_update(index_elements=list(keys), set_={"points": table.c.points + points})
    )


async def add_points(session: AsyncSession, user_id: int, power: int | None) -> None:
    """Carte obtenue (pas échangée ni offerte) : sa puissance compte pour le mois. Ne commit pas."""
    if not power or power <= 0 or not user_id:
        return
    key = month_key()
    await _add(session, MonthlyScore, {"user_id": user_id, "month_key": key}, int(power))
    member = await session.get(GuildMember, user_id)
    if member:
        await _add(session, GuildMonthlyScore, {"guild_id": member.guild_id, "month_key": key}, int(power))


def _ranked(rows) -> list[tuple[int, int, int]]:
    """[(id, points)] trié → [(rang, id, points)] ; ex æquo au même rang."""
    out, rank, previous = [], 0, None
    for position, (row_id, points) in enumerate(rows, start=1):
        if points != previous:
            rank, previous = position, points
        out.append((rank, row_id, points))
    return out


async def _solo(session: AsyncSession, key: str):
    rows = (await session.execute(
        select(MonthlyScore.user_id, MonthlyScore.points)
        .where(MonthlyScore.month_key == key, MonthlyScore.points > 0)
        .order_by(MonthlyScore.points.desc())
    )).all()
    return _ranked(rows)


async def _guilds(session: AsyncSession, key: str):
    rows = (await session.execute(
        select(GuildMonthlyScore.guild_id, GuildMonthlyScore.points)
        .join(Guild, Guild.id == GuildMonthlyScore.guild_id)
        .where(GuildMonthlyScore.month_key == key, GuildMonthlyScore.points > 0)
        .order_by(GuildMonthlyScore.points.desc())
    )).all()
    return _ranked(rows)


def _tier_for(tiers: list[dict], rank: int, total: int, points: int) -> dict | None:
    """Première tranche atteinte (les tranches vont de la meilleure à la plus large)."""
    for tier in tiers:
        if "rank" in tier and rank <= int(tier["rank"]):
            return tier
        if "top_pct" in tier and rank <= max(1, math.ceil(total * float(tier["top_pct"]) / 100)):
            return tier
        if "min_points" in tier and points >= int(tier["min_points"]):
            return tier
    return None


async def standings(session: AsyncSession, user: User, limit: int = 20) -> dict:
    """Classements du mois en cours (solo, guildes), ma place, tranches de récompenses."""
    await finalize_due(session)
    cfg = (await activities_config.get_config(session))["monthly"]
    key = month_key()
    solo, guilds = await _solo(session, key), await _guilds(session, key)

    users = {u.id: u for u in (await session.execute(
        select(User).where(User.id.in_([r[1] for r in solo[:limit]] + [user.id]))
    )).scalars().all()}
    guild_rows = {g.id: g for g in (await session.execute(
        select(Guild).where(Guild.id.in_([r[1] for r in guilds[:limit]]))
    )).scalars().all()}
    mine = next((r for r in solo if r[1] == user.id), None)
    member = await session.get(GuildMember, user.id)
    my_guild = next((r for r in guilds if member and r[1] == member.guild_id), None)
    last = (await session.execute(select(MonthlyResult).order_by(MonthlyResult.month_key.desc()))).scalars().first()

    return {
        "month_key": key, "month_label": month_label(key), "ends_at": month_end(key),
        "solo": [{"rank": r, "user_id": uid, "display_name": users[uid].display_name if uid in users else "?",
                  "points": p} for r, uid, p in solo[:limit]],
        "guilds": [{"rank": r, "guild_id": gid, "name": guild_rows[gid].name, "tag": guild_rows[gid].tag,
                    "icon": guild_rows[gid].icon, "color": guild_rows[gid].color, "points": p}
                   for r, gid, p in guilds[:limit] if gid in guild_rows],
        "me": {"rank": mine[0], "points": mine[2]} if mine else {"rank": None, "points": 0},
        "my_guild": {"rank": my_guild[0], "points": my_guild[2]} if my_guild else None,
        "players": len(solo),
        "solo_rewards": [{"label": t["label"], "rewards": await message_rewards.describe(session, t["rewards"])}
                         for t in cfg["solo_rewards"]],
        "guild_rewards": [{"label": t["label"], "rewards": await message_rewards.describe(session, t["rewards"])}
                          for t in cfg["guild_rewards"]],
        "last_champion": await champion_of(session, last) if last else None,
    }


async def champion_of(session: AsyncSession, result: MonthlyResult) -> dict:
    champion = await session.get(User, result.champion_user_id) if result.champion_user_id else None
    guild = await session.get(Guild, result.champion_guild_id) if result.champion_guild_id else None
    return {"month_label": month_label(result.month_key),
            "user_id": champion.id if champion else None,
            "display_name": champion.display_name if champion else None,
            "guild_name": guild.name if guild else None}


async def champion_badge(session: AsyncSession, user_id: int) -> str | None:
    """« Champion de septembre 2026 » pour le vainqueur du dernier mois clôturé."""
    last = (await session.execute(select(MonthlyResult).order_by(MonthlyResult.month_key.desc()))).scalars().first()
    if last and last.champion_user_id == user_id:
        return f"Champion de {month_label(last.month_key)}"
    return None


async def finalize_due(session: AsyncSession) -> None:
    """Clôture les mois terminés qui ne le sont pas encore (une seule fois, même
    si plusieurs requêtes arrivent en même temps). Commit si quelque chose a été clôturé."""
    current = month_key()
    pending = (await session.execute(
        select(MonthlyScore.month_key).where(MonthlyScore.month_key < current)
        .where(MonthlyScore.month_key.not_in(select(MonthlyResult.month_key))).distinct()
    )).scalars().all()
    if not pending:
        return
    if session.bind.dialect.name == "postgresql":
        await session.execute(text("SELECT pg_advisory_xact_lock(:s, 0)"), {"s": _FINALIZE_LOCK_SPACE})
    for key in sorted(pending):
        if await session.get(MonthlyResult, key, populate_existing=True):
            continue  # clôturé entre-temps par une autre requête
        await _finalize(session, key)
    await session.commit()


async def _finalize(session: AsyncSession, key: str) -> None:
    cfg = (await activities_config.get_config(session))["monthly"]
    label = month_label(key)
    solo, guilds = await _solo(session, key), await _guilds(session, key)

    for rank, user_id, points in solo:
        tier = _tier_for(cfg["solo_rewards"], rank, len(solo), points)
        if tier:
            await _reward(session, user_id, f"Défi de {label} : {tier['label']}",
                          f"Tu termines {rank}e du défi de {label} avec {points:,} points.".replace(",", " "),
                          tier["rewards"])
    for rank, guild_id, points in guilds:
        tier = _tier_for(cfg["guild_rewards"], rank, len(guilds), points)
        if not tier:
            continue
        members = (await session.execute(select(GuildMember.user_id).where(GuildMember.guild_id == guild_id))).scalars().all()
        for user_id in members:
            await _reward(session, user_id, f"Défi de {label} : guilde {tier['label']}",
                          f"Ta guilde termine {rank}e du défi de {label}.", tier["rewards"])

    session.add(MonthlyResult(
        month_key=key, champion_user_id=solo[0][1] if solo else None,
        champion_guild_id=guilds[0][1] if guilds else None,
    ))


async def _reward(session: AsyncSession, user_id: int, subject: str, body: str, rewards: list[dict]) -> None:
    items = await message_rewards.validate(session, rewards) if rewards else None
    session.add(Message(sender_type="admin", sender_user_id=None, recipient_user_id=user_id,
                        subject=subject[:100], body=body, reward_items=items))

