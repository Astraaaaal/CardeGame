"""
Expéditions : départ d'une équipe (1 à 3 cartes), cartes bloquées pendant la
mission, butin tiré au départ et crédité une seule fois au retour.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.activity import Expedition
from app.models.booster import Booster
from app.models.card import UserCard
from app.services import booster_inventory, expeditions, messages
from app.services.wallet import get_balance
from tests.conftest import make_user


async def _cards(session, user, powers):
    cards = [UserCard(user_id=user.id, character_id="c", set_id="s", rarity_id="rare", quality_id="fair",
                      specialty_id="normal", jewelry_id="none", power=p) for p in powers]
    session.add_all(cards)
    session.add(Booster(id="booster_A1", name="Booster A1", set_id="s", price=1, resource_id="coins"))
    await session.commit()
    return [c.id for c in cards]


async def test_team_power_scales_loot_and_cards_are_locked(session):
    user = await make_user(session)
    ids = await _cards(session, user, [2000, 2000, 1000, 10])

    weak = expeditions.estimate(60, 0, await _cfg(session))
    out = await expeditions.start(session, user, 0, 60, ids[:3])
    assert out["total_power"] == 5000
    assert out["estimate"]["coins"] == weak["coins"] * 2  # 5 000 de puissance = ×2

    with pytest.raises(HTTPException) as exc:
        await expeditions.start(session, user, 0, 60, [ids[3]])
    assert exc.value.status_code == 409  # emplacement occupé
    with pytest.raises(HTTPException) as exc:
        await expeditions.start(session, user, 1, 60, [ids[0]])
    assert exc.value.status_code == 409  # carte déjà partie
    with pytest.raises(HTTPException):
        await expeditions.start(session, user, 1, 45, [ids[3]])  # durée inconnue
    with pytest.raises(HTTPException):
        await expeditions.start(session, user, 1, 60, ids)  # 4 cartes

    other = await make_user(session, "other")
    other.gift_policy = "everyone"
    session.add(other)
    await session.commit()
    with pytest.raises(HTTPException) as exc:
        await messages.send_gift(session, user, "other", "", "", "card", ids[0], None, None)
    assert exc.value.status_code == 409


async def test_claim_only_after_return_and_only_once(session):
    user = await make_user(session)
    ids = await _cards(session, user, [100])
    out = await expeditions.start(session, user, 0, 15, ids)

    with pytest.raises(HTTPException) as exc:
        await expeditions.claim(session, user, out["id"])
    assert exc.value.status_code == 400

    exp = await session.get(Expedition, out["id"])
    exp.ends_at = datetime.utcnow() - timedelta(seconds=1)
    exp.loot = {"coins": 123, "dust": 25, "booster": True, "rare_card": False}
    session.add(exp)
    await session.commit()

    coins_before = user.coins
    reward = await expeditions.claim(session, user, out["id"])
    assert (reward["coins"], reward["dust"], reward["booster_id"]) == (123, 25, "booster_A1")
    assert user.coins == coins_before + 123
    assert await get_balance(session, user, "dust") == 25
    assert [(o["booster_id"], o["quantity"]) for o in await booster_inventory.list_owned(session, user.id)] \
        == [("booster_A1", 1)]
    assert await expeditions.locked_card_ids(session, ids) == set()

    with pytest.raises(HTTPException) as exc:
        await expeditions.claim(session, user, out["id"])
    assert exc.value.status_code == 409


async def _cfg(session):
    from app.services import activities_config
    return await activities_config.get_config(session)
