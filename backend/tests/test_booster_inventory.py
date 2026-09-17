"""
Boosters non ouverts possédés (app/services/booster_inventory.py) — crédit
(récompenses de niveaux/achievements/quêtes) et consommation à l'ouverture.
"""

import pytest
from fastapi import HTTPException

from app.services import booster_inventory
from tests.conftest import make_user


async def test_grant_then_consume(session):
    user = await make_user(session)

    await booster_inventory.grant(session, user.id, "booster_A1", 2)
    await session.commit()

    owned = await booster_inventory.list_owned(session, user.id)
    assert owned == []  # le booster référencé n'existe pas en base -> filtré silencieusement

    # Le compteur brut est bien incrémenté même si list_owned() le masque
    # (jointure sur un booster qui n'existe pas dans ce test) : on vérifie
    # via consume(), qui ne dépend pas de l'existence du Booster.
    await booster_inventory.consume(session, user.id, "booster_A1", 1)
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await booster_inventory.consume(session, user.id, "booster_A1", 5)
    assert exc_info.value.status_code == 400


async def test_consume_without_owning_raises(session):
    user = await make_user(session)

    with pytest.raises(HTTPException) as exc_info:
        await booster_inventory.consume(session, user.id, "booster_A1", 1)
    assert exc_info.value.status_code == 400


async def _booster(session, price=100):
    from app.models.booster import Booster
    booster = Booster(id="booster_T", name="Booster test", set_id="set_t", price=price, resource_id="coins")
    session.add(booster)
    await session.commit()
    return booster


async def test_buy_to_inventory_charges_discounted_price_and_keeps_boosters(session):
    user = await make_user(session)
    await _booster(session, price=100)

    result = await booster_inventory.buy_to_inventory(session, user, "booster_T", 5)

    assert result["total_cost"] == 450  # -10 % dès 5, comme un achat ouvert tout de suite
    assert user.coins == 500 - 450
    assert user.packs_opened == 0  # pas ouvert
    owned = await booster_inventory.list_owned(session, user.id)
    assert [(o["booster_id"], o["quantity"], o["bonus_id"]) for o in owned] == [("booster_T", 5, None)]


async def test_bonus_boosters_stack_by_identical_bonus(session):
    user = await make_user(session)
    await _booster(session)

    await booster_inventory.grant_bonus(session, user.id, "booster_T", "epic", None, "Épique garanti")
    await booster_inventory.grant_bonus(session, user.id, "booster_T", "epic", None, "Épique garanti")
    await booster_inventory.grant_bonus(session, user.id, "booster_T", None, 2.0, "Chances x2")
    await booster_inventory.grant_bonus(session, user.id, "booster_T", None, None, "Sans bonus")
    await session.commit()

    owned = await booster_inventory.list_owned(session, user.id)
    summary = sorted((o["quantity"], o["bonus_label"] or "") for o in owned)
    assert summary == [(1, ""), (1, "Chances x2"), (2, "Épique garanti")]


async def test_cannot_open_someone_elses_bonus_booster(session):
    alice, bob = await make_user(session, "alice"), await make_user(session, "bob")
    await _booster(session)
    await booster_inventory.grant_bonus(session, alice.id, "booster_T", "epic", None, "Épique garanti")
    await session.commit()
    bonus_id = (await booster_inventory.list_owned(session, alice.id))[0]["bonus_id"]

    with pytest.raises(HTTPException) as exc_info:
        await booster_inventory.open_owned(session, bob, "booster_T", 1, bonus_id)
    assert exc_info.value.status_code == 400
