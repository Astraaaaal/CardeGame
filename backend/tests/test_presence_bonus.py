"""
Présence : bonus de chance qui monte avec la présence continue et retombe
après une absence ; coffre d'absence rempli pendant l'absence, plafonné.
"""

from datetime import datetime, timedelta

from app.models.activity import UserActivity
from app.services import presence_bonus
from app.services.wallet import get_balance
from tests.conftest import make_user


async def test_multiplier_grows_with_presence_and_resets_after_absence(session):
    user = await make_user(session)
    first = await presence_bonus.ping(session, user)
    assert first["multiplier"] == 1.0

    row = await session.get(UserActivity, user.id)
    row.presence_since = datetime.utcnow() - timedelta(hours=2, minutes=30)  # moitié du parcours
    session.add(row)
    await session.commit()
    half = await presence_bonus.ping(session, user)
    assert 1.7 < half["multiplier"] < 1.8  # 1 + 1,5 × 0,5
    assert await presence_bonus.luck_multiplier(session, user.id) == half["multiplier"]

    row.presence_since = datetime.utcnow() - timedelta(hours=9)
    session.add(row)
    await session.commit()
    assert (await presence_bonus.ping(session, user))["multiplier"] == 2.5  # plafond

    # Absence de 10 minutes : le bonus repart de zéro.
    row.presence_ping_at = datetime.utcnow() - timedelta(minutes=10)
    session.add(row)
    await session.commit()
    assert await presence_bonus.luck_multiplier(session, user.id) == 1.0
    assert (await presence_bonus.ping(session, user))["multiplier"] == 1.0


async def test_absence_fills_chest_up_to_cap(session):
    user = await make_user(session)
    await presence_bonus.ping(session, user)
    row = await session.get(UserActivity, user.id)

    row.presence_ping_at = datetime.utcnow() - timedelta(hours=3)
    session.add(row)
    await session.commit()
    status = await presence_bonus.ping(session, user)
    assert status["chest"]["coins"] == 300 and status["chest"]["dust"] == 60

    row.presence_ping_at = datetime.utcnow() - timedelta(hours=30)
    session.add(row)
    await session.commit()
    status = await presence_bonus.ping(session, user)
    assert status["chest"]["hours"] == 12  # plafond

    coins_before = user.coins
    claimed = await presence_bonus.claim_chest(session, user)
    assert claimed["coins"] == 1_200
    assert user.coins == coins_before + 1_200
    assert await get_balance(session, user, "dust") == 240
    assert (await presence_bonus.status(session, user))["chest"]["coins"] == 0
