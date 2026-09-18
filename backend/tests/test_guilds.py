"""
Guildes : création payante, adhésion selon le mode, délai après un départ,
passation au chef, défi hebdomadaire (paliers), coffre, bonus et classements.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.guild import Guild, GuildMember, GuildWeek
from app.services import guilds, quest_progress
from tests.conftest import make_user


async def _rich(session, name, coins=10_000):
    user = await make_user(session, name)
    user.coins = coins
    session.add(user)
    await session.commit()
    return user


async def test_create_costs_coins_and_names_are_unique(session):
    alice = await _rich(session, "alice")
    guild = await guilds.create(session, alice, "Les Arcanistes", "arc", "🐉", "#ff0000", "open")
    assert guild.tag == "ARC" and alice.coins == 8_000
    assert (await session.get(GuildMember, alice.id)).role == "leader"

    bob = await _rich(session, "bob")
    with pytest.raises(HTTPException):
        await guilds.create(session, bob, "Autre", "ARC", "🐉", "#fff", "open")  # tag pris
    with pytest.raises(HTTPException):
        await guilds.create(session, bob, "les arcanistes", "XYZ", "🐉", "#fff", "open")  # nom pris


async def test_join_policies_and_leave_cooldown(session):
    alice = await _rich(session, "alice")
    bob = await _rich(session, "bob")
    carol = await _rich(session, "carol")
    guild = await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "request")

    assert await guilds.join(session, bob, guild.id) == "requested"
    detail = await guilds.detail(session, alice)
    [req] = detail["requests"]
    await guilds.answer_request(session, alice, req["id"], True)
    assert (await session.get(GuildMember, bob.id)).guild_id == guild.id

    await guilds.update_settings(session, alice, {"join_policy": "invite"})
    with pytest.raises(HTTPException):
        await guilds.join(session, carol, guild.id)
    await guilds.invite(session, alice, "carol")
    [inv] = await guilds.my_invites(session, carol)
    await guilds.answer_invite(session, carol, inv["id"], True)
    assert (await session.get(GuildMember, carol.id)).guild_id == guild.id

    await guilds.leave(session, carol)
    with pytest.raises(HTTPException) as exc:
        await guilds.join(session, carol, guild.id)
    assert "min" in exc.value.detail  # délai de 4 h
    carol.guild_left_at = datetime.utcnow() - timedelta(hours=5)
    session.add(carol)
    await session.commit()
    await guilds.invite(session, alice, "carol")
    [inv] = await guilds.my_invites(session, carol)
    await guilds.answer_invite(session, carol, inv["id"], True)


async def test_leader_leaving_promotes_oldest_officer(session):
    alice = await _rich(session, "alice")
    bob = await _rich(session, "bob")
    carol = await _rich(session, "carol")
    guild = await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "open")
    await guilds.join(session, bob, guild.id)
    await guilds.join(session, carol, guild.id)
    await guilds.set_role(session, alice, carol.id, "officer")

    await guilds.leave(session, alice)
    assert (await session.get(GuildMember, carol.id)).role == "leader"
    assert (await session.get(GuildMember, bob.id)).role == "member"


async def test_weekly_challenge_tracks_contributions_and_moves_tiers(session):
    alice = await _rich(session, "alice")
    guild = await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "open")
    week = await guilds.current_week(session, guild)
    await session.commit()
    objective = week.objectives[0]

    await quest_progress.increment(session, alice.id, objective["metric"], objective["target"])
    await session.commit()
    week = await session.get(GuildWeek, (guild.id, week.week_key))
    assert week.objectives[0]["completed_at"]
    assert guild.xp == 300  # XP de l'objectif (palier 1)

    coins = alice.coins
    reward = await guilds.claim_objective(session, alice, objective["metric"])
    assert alice.coins == coins + reward["coins"] == coins + 150
    with pytest.raises(HTTPException):
        await guilds.claim_objective(session, alice, objective["metric"])

    # Semaine précédente réussie (3/3) : palier suivant ; ratée : moitié du palier.
    week.week_key = "2000-W01"
    week.objectives = [{**o, "completed_at": "x"} for o in week.objectives]
    session.add(week)
    await session.commit()
    new_week = await guilds.current_week(session, guild)
    assert new_week.tier == 2 and guild.challenge_best_tier == 2

    guild.challenge_tier = 6
    new_week.tier = 6
    new_week.week_key = "2000-W02"
    session.add_all([guild, new_week])
    await session.commit()
    third = await guilds.current_week(session, guild)
    assert third.tier == 3


async def test_donations_feed_chest_xp_and_buy_buffs(session):
    alice = await _rich(session, "alice", coins=20_000)
    guild = await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "open")

    res = await guilds.donate(session, alice, "coins", 5_005)
    assert res == {"points": 500, "spent": 5_000}
    assert (guild.chest_points, guild.chest_total, guild.xp) == (500, 500, 500)

    assert await guilds.buff_value(session, alice.id, "luck") is None
    await guilds.buy_buff(session, alice, "luck")
    assert guild.chest_points == 0
    assert await guilds.buff_value(session, alice.id, "luck") == 1.5
    with pytest.raises(HTTPException):
        await guilds.buy_buff(session, alice, "luck")  # plus de points


async def test_rankings_average_three_boards(session):
    alice = await _rich(session, "alice", coins=50_000)
    bob = await _rich(session, "bob", coins=50_000)
    g1 = await guilds.create(session, alice, "Première", "ONE", "🛡️", "#fff", "open")
    await guilds.create(session, bob, "Seconde", "TWO", "🛡️", "#fff", "open")
    await guilds.donate(session, alice, "coins", 30_000)

    overall = await guilds.rankings(session, "overall")
    assert overall[0]["id"] == g1.id and overall[0]["rank"] == 1
    assert [r["tag"] for r in await guilds.rankings(session, "chest")] == ["ONE", "TWO"]
    assert (await session.get(Guild, g1.id)).chest_total == 3_000
