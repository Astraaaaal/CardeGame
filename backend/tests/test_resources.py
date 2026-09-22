"""
Ressources de recyclage : ce que rapporte une carte (plages selon la puissance
relative), ressources de la machine (obligatoires puis facultatives, plafond par
cran) et paires du convertisseur.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import activities_config, booster_inventory, machine, recycling, resource_catalog
from app.services.wallet import apply_delta, get_balance
from tests.test_machine import _roll, _today, _user_with_booster

CFG = activities_config.DEFAULTS


def _card(power, **tiers):
    base = {"rarity_id": "legendary", "quality_id": "authentic", "specialty_id": "shiny", "jewelry_id": "gold"}
    # drop_probability 0,01 → plage de puissance [1, 100].
    return SimpleNamespace(power=power, drop_probability=0.01, **{**base, **tiers})


def test_best_roll_forks_sit_at_the_top_of_every_range():
    # Cible au maximum, fourchette de -30 % jusqu'au maximum.
    assert recycling.card_forks(_card(100), CFG) == {
        "dust": (700, 1000), "frag_legendary": (7, 10), "gold_nugget": (3, 5), "glitter": (5, 8), "dust_star": (10, 15)}


def test_weakest_roll_forks_stay_at_the_minimum_and_common_tiers_only_dust():
    assert recycling.card_forks(_card(1), CFG) == {
        "dust": (100, 130), "frag_legendary": (1, 2), "gold_nugget": (1, 2), "glitter": (1, 2), "dust_star": (1, 2)}
    plain = _card(50, rarity_id="common", quality_id="scratched", specialty_id="normal", jewelry_id="none")
    assert recycling.card_forks(plain, CFG) == {"dust": (2, 4)}  # cible 1 + 4 × 49/99 ≈ 3


def test_yield_is_drawn_inside_the_fork():
    card = _card(60)
    forks = recycling.card_forks(card, CFG)
    for _ in range(50):
        gains = recycling.card_yield(card, CFG)
        assert all(forks[r][0] <= q <= forks[r][1] for r, q in gains.items())


def test_converter_pairs_link_each_family_both_ways_and_to_dust():
    listed = resource_catalog.converter_pairs()
    pairs = {(p["from"], p["to"]): p for p in listed}
    assert len(pairs) == len(listed)  # aucune paire en double
    assert pairs[("frag_rare", "frag_epic")]["give"] == 10 and pairs[("frag_epic", "frag_rare")]["get"] == 5
    assert ("prism_crystal", "dust") in pairs and ("dust", "prism_crystal") in pairs
    # Les poussières de qualité passent par leur famille (monter 10 → 1, descendre 1 → 5).
    assert pairs[("dust", "dust_fine")]["give"] == 10 and pairs[("dust_fine", "dust")]["get"] == 5


async def test_resource_required_from_the_third_step(session, monkeypatch):
    user = await _user_with_booster(session)
    _today(monkeypatch, ["rarity_chances"])
    _roll(monkeypatch, 0.0)
    bonus_id = None  # booster sans bonus, puis celui obtenu à chaque cran
    for _ in range(2):  # crans 1 et 2 : pièces seules
        res = await machine.upgrade(session, user, "booster", "rarity_chances", booster_id="b", bonus_id=bonus_id)
        bonus_id = next(o["bonus_id"] for o in await booster_inventory.list_owned(session, user.id) if o["bonus_id"])
        assert res["success"]

    [upgrade] = [i for i in res["state"]["items"] if i.get("bonus_id") == bonus_id][0]["upgrades"]
    assert upgrade["required"] == {"resource_id": "frag_epic", "amount": 2, "name": "frag_epic"}
    with pytest.raises(HTTPException) as exc:  # cran 3 sans fragments épiques
        await machine.upgrade(session, user, "booster", "rarity_chances", booster_id="b", bonus_id=bonus_id)
    assert "manque 2" in exc.value.detail

    await apply_delta(session, user, "frag_epic", 5)
    await session.commit()
    res = await machine.upgrade(session, user, "booster", "rarity_chances", booster_id="b", bonus_id=bonus_id)
    assert res["success"] and res["spent"]["frag_epic"] == 2
    assert await get_balance(session, user, "frag_epic") == 3


async def test_added_resources_raise_the_chance_up_to_the_step_cap(session, monkeypatch):
    user = await _user_with_booster(session)
    _today(monkeypatch, ["jewelry_guarantee"])
    await apply_delta(session, user, "silver_ore", 100)
    await apply_delta(session, user, "gold_nugget", 5)
    await session.commit()
    _roll(monkeypatch, 0.99)  # premier cran : plafond 100 %, 0,99 passe avec assez d'argent brut

    res = await machine.upgrade(session, user, "booster", "jewelry_guarantee", booster_id="b",
                                extra={"silver_ore": 40})
    assert res["chance"] == 1.0 and res["success"]
    assert await get_balance(session, user, "silver_ore") == 60

    with pytest.raises(HTTPException):  # ressource sans lien avec l'amélioration
        await machine.upgrade(session, user, "booster", "jewelry_guarantee", booster_id="b", extra={"frag_rare": 1})


def test_step_caps_never_guarantee_high_steps():
    assert machine.bonus_cap(CFG, 0) == 1.0
    assert machine.bonus_cap(CFG, 1) == 0.85
    assert machine.bonus_cap(CFG, 9) == 0.40
    assert machine.chance_with_extra(CFG, "jewelry_guarantee", 4, 0.1, {"prism_crystal": 50}) == 0.40
    assert machine.chance_with_extra(CFG, "jewelry_guarantee", 1, 0.2, {"silver_ore": 5}) == pytest.approx(0.3)
