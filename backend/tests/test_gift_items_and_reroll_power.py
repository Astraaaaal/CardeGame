"""
Cadeaux de boosters à bonus et de rerolls (règles conservées), et puissance
d'une carte au reroll : conservée si seule une autre caractéristique est
relancée, redescendue au maximum possible si la combinaison devient plus commune.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.models.card import UserCard
from app.models.character import CharacterSet
from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.services import booster_inventory, messages, reroll_inventory
from app.services.power import power_range
from app.services.reroll import apply_reroll
from tests.conftest import make_user


async def _pair(session):
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    bob.gift_policy = "everyone"
    session.add(bob)
    await session.commit()
    return alice, bob


async def test_gift_bonus_booster_keeps_its_bonus(session):
    from app.models.booster import Booster
    session.add(Booster(id="booster_T", name="Booster test", set_id="s", price=1, resource_id="coins"))
    alice, bob = await _pair(session)
    await booster_inventory.grant_bonus(session, alice.id, "booster_T", "epic", 2.0, "Épique garanti", 3)
    await session.commit()
    [owned] = await booster_inventory.list_owned(session, alice.id)

    msg = await messages.send_gift(session, alice, "bob", "", "", "booster", None, None, 2,
                                   booster_id="booster_T", bonus_id=owned["bonus_id"])
    await messages.claim(session, msg)

    [alice_left] = await booster_inventory.list_owned(session, alice.id)
    assert alice_left["quantity"] == 1
    [received] = await booster_inventory.list_owned(session, bob.id)
    assert (received["quantity"], received["bonus_label"]) == (2, "Épique garanti")


async def test_gift_reroll_tokens_keep_rules(session):
    alice, bob = await _pair(session)
    rules = {"reroll_rarity": True, "reroll_quality": False, "reroll_specialty": False,
             "reroll_jewelry": False, "reroll_power": False, "reroll_mode": "guaranteed_min"}
    await reroll_inventory.grant_rules(session, alice.id, None, "Reroll rareté", rules, 2)
    await session.commit()
    [token] = await reroll_inventory.list_owned(session, alice.id)

    with pytest.raises(HTTPException):
        await messages.send_gift(session, alice, "bob", "", "", "reroll", None, None, 3, reroll_token_id=token["id"])

    msg = await messages.send_gift(session, alice, "bob", "", "", "reroll", None, None, 2, reroll_token_id=token["id"])
    assert await reroll_inventory.list_owned(session, alice.id) == []
    await messages.claim(session, msg)
    [received] = await reroll_inventory.list_owned(session, bob.id)
    assert (received["quantity"], received["axes"], received["reroll_mode"]) == (2, ["rarity"], "guaranteed_min")


async def _references(session):
    session.add(CharacterSet(character_id="c", set_id="s", weight=1))
    session.add_all([
        Rarity(id="common", name="Commune", weight=1000), Rarity(id="legendary", name="Légendaire", weight=1),
        Quality(id="fair", name="Correcte", weight=1), Specialty(id="normal", name="Normale", weight=1),
        Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()


def _rules(**on):
    base = dict(reroll_rarity=False, reroll_quality=False, reroll_specialty=False,
                reroll_jewelry=False, reroll_power=False, reroll_mode="random")
    return SimpleNamespace(**{**base, **on})


async def test_reroll_other_axis_keeps_power_but_caps_it_to_new_range(session):
    await _references(session)
    user = await make_user(session)
    card = UserCard(user_id=user.id, character_id="c", set_id="s", rarity_id="legendary",
                    quality_id="fair", specialty_id="normal", jewelry_id="none",
                    drop_probability=1 / 1001, power=900)
    session.add(card)
    await session.commit()

    # Garanti égal ou mieux : reste légendaire -> puissance inchangée.
    await apply_reroll(session, card, _rules(reroll_rarity=True, reroll_mode="guaranteed_min"))
    assert (card.rarity_id, card.power) == ("legendary", 900)

    # Forcé vers la commune (poids écrasant) : la plage max redescend sous 900.
    card.power = 900
    for _ in range(20):
        await apply_reroll(session, card, _rules(reroll_rarity=True))
        if card.rarity_id == "common":
            break
    assert card.rarity_id == "common"
    cap = power_range(card.drop_probability, card.rarity_id, card.quality_id, card.specialty_id, card.jewelry_id)
    assert cap < 900 and card.power == cap
