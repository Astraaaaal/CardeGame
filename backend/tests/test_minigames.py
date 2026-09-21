"""
Mini-jeux : « plus ou moins » (gain selon la probabilité réelle du pari,
égalité neutre qui compte comme une manche, encaissement dès 3 manches,
défaite = mise perdue) et roue de la
fortune (tour gratuit quotidien, tours payants plafonnés).
"""

import pytest
from fastapi import HTTPException

from app.models.game_config import GameConfig
from app.services import activities_config, minigames
from app.services.wallet import get_balance
from tests.conftest import make_user


def _fake_cards(monkeypatch, powers):
    queue = list(powers)

    async def fake(session, cfg):
        return {"character_name": "Test", "power": queue.pop(0)}

    async def fake_sample(session, cfg):
        return list(range(1, 1001))  # puissances uniformes de 1 à 1000

    monkeypatch.setattr(minigames, "_random_card", fake)
    monkeypatch.setattr(minigames, "_power_sample", fake_sample)


async def test_gain_depends_on_the_real_odds(session, monkeypatch):
    _fake_cards(monkeypatch, [])
    cfg = await activities_config.get_config(session)
    odds = await minigames._guess_multipliers(session, cfg, 100)
    # 900 cartes au-dessus sur 1000 (1 égalité) : pari facile, gain faible.
    assert odds["higher"] == round(0.98 * 0.999 / 0.9, 2)
    assert odds["lower"] == round(0.98 * 0.999 / 0.099, 2)  # 99 cartes en dessous : pari risqué
    assert (await minigames._guess_multipliers(session, cfg, 20))["lower"] == 20  # plafonné
    assert (await minigames._guess_multipliers(session, cfg, 1000))["higher"] is None


async def test_higher_lower_tie_counts_and_cashout_from_step_three(session, monkeypatch):
    user = await make_user(session)
    _fake_cards(monkeypatch, [500, 500, 750, 900, 100])

    game = await minigames.higher_lower_start(session, user, "coins", 100)
    assert user.coins == 400
    res = await minigames.higher_lower_guess(session, user, game["id"], "lower")  # 500 -> 500
    assert (res["outcome"], res["step"], res["total_multiplier"]) == ("tie", 1, 1.0)
    res = await minigames.higher_lower_guess(session, user, game["id"], "higher")  # 500 -> 750 (p = 0,5)
    assert (res["outcome"], res["step"]) == ("win", 2) and not res["can_cashout"]
    with pytest.raises(HTTPException):
        await minigames.higher_lower_cashout(session, user, game["id"])  # avant 3 manches

    res = await minigames.higher_lower_guess(session, user, game["id"], "higher")  # 750 -> 900 (p = 0,25)
    assert res["step"] == 3 and res["can_cashout"]
    m1 = round(0.98 * 0.999 / 0.5, 2)
    m2 = round(0.98 * 0.999 / 0.25, 2)
    assert res["cashout_value"] == int(100 * m1 * m2)

    await minigames.higher_lower_cashout(session, user, game["id"])
    assert user.coins == 400 + int(100 * m1 * m2)


async def test_higher_lower_loss_and_rules(session, monkeypatch):
    user = await make_user(session)
    _fake_cards(monkeypatch, [800, 200])

    with pytest.raises(HTTPException):
        await minigames.higher_lower_start(session, user, "shards", 100)  # jamais la monnaie premium
    with pytest.raises(HTTPException):
        await minigames.higher_lower_start(session, user, "coins", 10)  # sous la mise minimum

    game = await minigames.higher_lower_start(session, user, "coins", 200)
    with pytest.raises(HTTPException) as exc:
        await minigames.higher_lower_start(session, user, "coins", 50)
    assert exc.value.status_code == 409  # une partie à la fois

    res = await minigames.higher_lower_guess(session, user, game["id"], "higher")  # 800 -> 200
    assert (res["outcome"], res["status"]) == ("lose", "lost")
    assert user.coins == 300


async def test_wheel_free_spin_then_paid_spins_until_cap(session):
    user = await make_user(session)
    session.add(GameConfig(id=1))
    await session.commit()
    await activities_config.save_config(session, {"wheel": {
        "extra_spin_cost": 200, "extra_spins_per_day": 1,
        "segments": [{"label": "50 poussière", "kind": "resource", "id": "dust", "amount": 50, "weight": 1}],
    }})

    first = await minigames.wheel_spin(session, user)
    assert first["reward"]["amount"] == 50 and user.coins == 500
    assert first["state"]["free_available"] is False

    await minigames.wheel_spin(session, user)
    assert user.coins == 300
    assert await get_balance(session, user, "dust") == 100

    with pytest.raises(HTTPException):
        await minigames.wheel_spin(session, user)
