"""
Atelier : vitesse de taps plafonnée côté serveur, jauges qui rapportent des
pièces et des fragments, booster tous les 10 fragments, plafond quotidien.
"""

from datetime import datetime, timedelta

from app.models.activity import UserActivity
from app.models.booster import Booster
from app.services import booster_inventory, workshop
from tests.conftest import make_user


async def _rewind(session, user, seconds):
    row = await session.get(UserActivity, user.id)
    row.workshop_last_at = datetime.utcnow() - timedelta(seconds=seconds)
    session.add(row)
    await session.commit()


async def test_tap_speed_is_capped_like_a_human(session):
    user = await make_user(session)
    await workshop.status(session, user)
    await _rewind(session, user, 1)
    res = await workshop.tap(session, user, 1_000)  # auto-clicker
    assert res["accepted"] == 10  # 10 taps/s au plus

    await _rewind(session, user, 60)
    res = await workshop.tap(session, user, 1_000)
    assert res["accepted"] == 30  # une longue pause ne donne pas plus de 3 s de crédit


async def test_gauges_pay_coins_fragments_then_a_booster_and_stop_at_daily_cap(session):
    user = await make_user(session)
    session.add(Booster(id="booster_A1", name="Booster A1", set_id="s", price=1, resource_id="coins"))
    await session.commit()
    row = await workshop.status(session, user)
    coins = user.coins

    # Force 10 jauges d'un coup (taps déjà presque pleins).
    activity = await session.get(UserActivity, user.id)
    activity.workshop_taps = 100 * 10 - 5
    session.add(activity)
    await session.commit()
    await _rewind(session, user, 1)
    res = await workshop.tap(session, user, 5)
    assert res["reward"]["gauges"] == 10
    assert user.coins == coins + 500
    assert res["reward"]["boosters"] == 1 and res["fragments"] == 0
    assert [(o["booster_id"], o["quantity"]) for o in await booster_inventory.list_owned(session, user.id)] \
        == [("booster_A1", 1)]

    activity.workshop_gauges_today = row["gauges_per_day"]
    session.add(activity)
    await session.commit()
    await _rewind(session, user, 1)
    res = await workshop.tap(session, user, 5)
    assert res["accepted"] == 0 and res["reward"]["gauges"] == 0
