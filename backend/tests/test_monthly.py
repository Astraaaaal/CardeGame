"""
Défi du mois : points par carte obtenue (solo et guilde), classement, clôture
du mois (récompenses par tranche envoyées par la messagerie, champions).
"""

from sqlmodel import select

from app.models.economy import Resource
from app.models.message import Message
from app.models.monthly import MonthlyResult, MonthlyScore
from app.services import guilds, monthly
from tests.conftest import make_user

PREVIOUS = "2026-08"


async def _resources(session):
    session.add_all([Resource(id=r, name=r) for r in
                     ("coins", "frag_rare", "frag_epic", "frag_legendary", "dust_star")])
    await session.commit()


async def test_points_count_for_the_player_and_their_guild(session):
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    alice.coins = 10_000
    await session.commit()
    await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "open")

    await monthly.add_points(session, alice.id, 300)
    await monthly.add_points(session, alice.id, 200)  # cumul atomique
    await monthly.add_points(session, bob.id, 400)    # sans guilde
    await monthly.add_points(session, bob.id, None)   # carte sans puissance : ignorée
    await session.commit()

    standings = await monthly.standings(session, alice)
    assert [(e["rank"], e["display_name"], e["points"]) for e in standings["solo"]] == [
        (1, "alice", 500), (2, "bob", 400)]
    assert standings["me"] == {"rank": 1, "points": 500}
    assert standings["my_guild"]["points"] == 500 and standings["guilds"][0]["points"] == 500


async def test_month_is_closed_once_with_rewards_and_champion(session):
    await _resources(session)
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    alice.coins = 10_000
    await session.commit()
    await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "open")
    session.add_all([
        MonthlyScore(user_id=alice.id, month_key=PREVIOUS, points=1000),
        MonthlyScore(user_id=bob.id, month_key=PREVIOUS, points=10),
    ])
    await session.commit()

    await monthly.finalize_due(session)
    result = await session.get(MonthlyResult, PREVIOUS)
    assert result and result.champion_user_id == alice.id

    messages = (await session.execute(select(Message))).scalars().all()
    by_user = {m.recipient_user_id: m for m in messages}
    assert "1re place" in by_user[alice.id].subject and by_user[alice.id].sender_type == "admin"
    assert [i["id"] for i in by_user[alice.id].reward_items] == ["coins", "frag_legendary", "dust_star"]
    assert "2e place" in by_user[bob.id].subject

    await monthly.finalize_due(session)  # deuxième passage : rien de plus
    assert len((await session.execute(select(Message))).scalars().all()) == len(messages)
    assert await monthly.champion_badge(session, alice.id) == f"Champion de {monthly.month_label(PREVIOUS)}"
    assert await monthly.champion_badge(session, bob.id) is None
