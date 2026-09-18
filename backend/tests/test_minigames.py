"""
Mini-jeux : « plus ou moins » (mise débitée, gain ×1,8 par bonne réponse,
égalité sans perte, défaite = mise perdue, encaissement) et roue de la
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

    monkeypatch.setattr(minigames, "_random_card", fake)


async def test_higher_lower_win_tie_then_cash_out(session, monkeypatch):
    user = await make_user(session)
    _fake_cards(monkeypatch, [100, 500, 500, 900])

    game = await minigames.higher_lower_start(session, user, "coins", 100)
    assert user.coins == 400

    res = await minigames.higher_lower_guess(session, user, game["id"], "higher")  # 100 -> 500
    assert (res["outcome"], res["step"]) == ("win", 1)
    res = await minigames.higher_lower_guess(session, user, game["id"], "lower")  # 500 -> 500
    assert (res["outcome"], res["step"]) == ("tie", 1)
    res = await minigames.higher_lower_guess(session, user, game["id"], "higher")  # 500 -> 900
    assert res["step"] == 2 and res["cashout_value"] == 324  # 100 × 1,8²

    await minigames.higher_lower_cashout(session, user, game["id"])
    assert user.coins == 400 + 324
    with pytest.raises(HTTPException):
        await minigames.higher_lower_guess(session, user, game["id"], "higher")


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
