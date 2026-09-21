"""
Machine d'amélioration (cran suivant, échec = prix payé + chance et prix en
hausse, jour risqué = objet détruit) et convertisseur (taux, limites du jour).
"""

import pytest
from fastapi import HTTPException

from app.models.booster import Booster
from app.models.reference import Rarity
from app.services import booster_inventory, machine, reroll_inventory
from app.services.wallet import get_balance
from tests.conftest import make_user


def _today(monkeypatch, kinds, event=None):
    monkeypatch.setattr(machine, "today_plan", lambda cfg, now=None: {"day": 1, "length": 14, "kinds": kinds, "event": event})


def _roll(monkeypatch, value):
    monkeypatch.setattr(machine.random, "random", lambda: value)


async def _user_with_booster(session):
    session.add_all([Booster(id="b", name="Booster", set_id="s", price=1, resource_id="coins"),
                     Rarity(id="rare", name="Rare", weight=1)])
    user = await make_user(session)
    user.coins = 100_000
    await booster_inventory.grant(session, user.id, "b", 2)
    await session.commit()
    return user


async def test_booster_upgrade_success_then_next_step(session, monkeypatch):
    user = await _user_with_booster(session)
    _today(monkeypatch, ["rarity_guarantee"])
    _roll(monkeypatch, 0.0)

    res = await machine.upgrade(session, user, "booster", "rarity_guarantee", booster_id="b")
    assert res["success"] and res["cost"] == 400
    owned = await booster_inventory.list_owned(session, user.id)
    assert sorted((o["bonus_id"] is None, o["force_min_rarity_id"], o["quantity"]) for o in owned) == [
        (False, "rare", 1), (True, None, 1)]

    bonus = next(o for o in owned if o["bonus_id"])
    [item] = [i for i in res["state"]["items"] if i.get("bonus_id") == bonus["bonus_id"]]
    assert item["upgrades"][0]["level"] == 1 and item["upgrades"][0]["cost"] == 720  # 400 × 1,8


async def test_failures_raise_chance_and_price_and_risky_day_destroys(session, monkeypatch):
    user = await _user_with_booster(session)
    _today(monkeypatch, ["rarity_chances"])
    _roll(monkeypatch, 0.99)

    first = await machine.upgrade(session, user, "booster", "rarity_chances", booster_id="b")
    assert not first["success"] and not first["destroyed"]
    nxt = first["state"]["items"][0]["upgrades"][0]
    assert nxt["cost"] == 500 and nxt["chance"] == pytest.approx(0.4)  # ×1,25 ; +5 points

    _today(monkeypatch, ["rarity_chances"], {"id": "risky", "label": "Risqué", "cost_factor": 0.4, "lose_on_fail": True})
    res = await machine.upgrade(session, user, "booster", "rarity_chances", booster_id="b")
    assert res["destroyed"] and res["cost"] == 200  # 500 × 0,4
    assert (await booster_inventory.list_owned(session, user.id))[0]["quantity"] == 1


async def test_reroll_guarantee_and_unavailable_kind(session, monkeypatch):
    user = await make_user(session)
    user.coins = 10_000
    rules = {"reroll_rarity": True, "reroll_quality": False, "reroll_specialty": False,
             "reroll_jewelry": False, "reroll_power": False, "reroll_mode": "random"}
    await reroll_inventory.grant_rules(session, user.id, None, "Reroll", rules, 1)
    await session.commit()
    [token] = await reroll_inventory.list_owned(session, user.id)

    _today(monkeypatch, ["rarity_chances"])
    with pytest.raises(HTTPException):
        await machine.upgrade(session, user, "reroll", "reroll_guarantee", token_id=token["id"])

    _today(monkeypatch, ["reroll_guarantee"])
    _roll(monkeypatch, 0.0)
    await machine.upgrade(session, user, "reroll", "reroll_guarantee", token_id=token["id"])
    [upgraded] = await reroll_inventory.list_owned(session, user.id)
    assert upgraded["reroll_mode"] == "guaranteed_min"


async def test_converter_rates_and_daily_limit(session):
    user = await make_user(session)
    user.coins = 5_000
    await session.commit()
    res = await machine.convert(session, user, "coins", "dust", 2000)
    assert res["gained"] == 200 and user.coins == 3_000
    assert await get_balance(session, user, "dust") == 200
    with pytest.raises(HTTPException):
        await machine.convert(session, user, "coins", "dust", 2010)  # au-delà du maximum
    with pytest.raises(HTTPException):
        await machine.convert(session, user, "coins", "dust", 15)  # pas un multiple de 10
    await machine.convert(session, user, "dust", "coins", 100)
    await machine.convert(session, user, "dust", "coins", 50)
    with pytest.raises(HTTPException):
        await machine.convert(session, user, "dust", "coins", 10)  # 3 conversions par jour


async def test_generator_applies_quality_and_jewelry_minimums(session):
    from app.models.character import Character, CharacterSet
    from app.models.reference import Jewelry, Quality, Specialty
    from app.services.card_generator import CardGeneratorService
    session.add_all([
        Character(id="c", name="C", type="feu"), CharacterSet(character_id="c", set_id="s", weight=1),
        Rarity(id="common", name="Commune", weight=1),
        Quality(id="fair", name="Correcte", weight=1000), Quality(id="mint", name="Mint", weight=1),
        Specialty(id="normal", name="Normale", weight=1),
        Jewelry(id="none", name="Aucun", weight=1000), Jewelry(id="gold", name="Or", weight=1),
    ])
    await session.commit()
    for _ in range(10):
        cards = await CardGeneratorService().generate_pack(
            session, ["s"], cards_count=2, guaranteed_rare=False,
            force_min_quality_id="mint", force_min_jewelry_id="gold",
        )
        assert (cards[-1]["quality_id"], cards[-1]["jewelry_id"]) == ("mint", "gold")



def test_cycle_of_fourteen_days_covers_every_upgrade_and_event():
    from datetime import datetime, timedelta
    from app.services.activities_config import DEFAULTS
    start = datetime(2026, 9, 21)
    plans = [machine.today_plan(DEFAULTS, start + timedelta(days=d)) for d in range(14)]
    assert [p["day"] for p in plans] == list(range(1, 15))
    upgrades = [p["kinds"][0] for p in plans if not p["event"]]
    assert sorted(upgrades) == sorted(DEFAULTS["machine"]["cycle_upgrades"])  # chaque amélioration une fois
    assert sorted(p["event"]["id"] for p in plans if p["event"]) == ["lucky", "risky", "sale"]
    assert all(len(p["kinds"]) == 1 for p in plans)
    # Cycle suivant : autre ordre, même contenu.
    nxt = [machine.today_plan(DEFAULTS, start + timedelta(days=14 + d)) for d in range(14)]
    assert sorted(p["kinds"][0] for p in nxt if not p["event"]) == sorted(upgrades)


async def test_power_rolls_keep_the_best_but_never_exceed_max():
    from app.services.power import roll_drawn_power
    data = {"drop_probability": 0.01, "rarity_id": "common", "quality_id": "fair",
            "specialty_id": "normal", "jewelry_id": "none"}
    single = sum(roll_drawn_power(data) for _ in range(2000)) / 2000
    best_of_5 = [roll_drawn_power(data, rolls=5) for _ in range(2000)]
    assert max(best_of_5) <= 100 and sum(best_of_5) / 2000 > single + 20
