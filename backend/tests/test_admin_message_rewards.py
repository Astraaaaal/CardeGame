"""
Messages admin à récompenses multiples : ressource, booster à bonus, reroll
à règles libres et carte unique (puissance fixe plafonnée), validés à l'envoi
et crédités à la récupération.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models.booster import Booster
from app.models.card import UserCard
from app.models.character import Character, CharacterSet
from app.models.message import Message
from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.services import booster_inventory, messages, reroll_inventory
from tests.conftest import make_user

REWARDS = [
    {"kind": "resource", "id": "coins", "amount": 250},
    {"kind": "booster", "id": "booster_T", "quantity": 2, "force_min_rarity_id": "legendary",
     "rarity_weight_multiplier": 3, "label": "Cadeau de l'équipe"},
    {"kind": "reroll", "label": "Reroll offert", "quantity": 3,
     "rules": {"reroll_quality": True, "reroll_mode": "guaranteed_min"}},
    {"kind": "card", "character_id": "c", "rarity_id": "legendary", "quality_id": "fair",
     "specialty_id": "normal", "jewelry_id": "none", "power_mode": "fixed", "power": 999_999},
]


async def _content(session):
    session.add_all([
        Booster(id="booster_T", name="Booster test", set_id="s", price=1, resource_id="coins"),
        Character(id="c", name="Pika", type="t"), CharacterSet(character_id="c", set_id="s", weight=1),
        Rarity(id="common", name="Commune", weight=99), Rarity(id="legendary", name="Légendaire", weight=1),
        Quality(id="fair", name="Correcte", weight=1), Specialty(id="normal", name="Normale", weight=1),
        Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()


async def test_admin_message_grants_every_reward_once(session):
    await _content(session)
    user = await make_user(session)

    assert await messages.send_admin_broadcast(session, ["test_user"], "Merci", "", None, None, REWARDS) == 1
    msg = (await session.execute(select(Message))).scalars().one()

    out = await messages.build_out(session, msg)
    assert out.has_reward
    assert [i.kind for i in out.reward_items] == ["resource", "booster", "reroll", "card"]
    assert out.reward_items[3].card.character_name == "Pika"

    await messages.claim(session, msg)
    assert user.coins == 500 + 250
    [booster] = await booster_inventory.list_owned(session, user.id)
    assert (booster["quantity"], booster["bonus_label"]) == (2, "Cadeau de l'équipe")
    [token] = await reroll_inventory.list_owned(session, user.id)
    assert (token["quantity"], token["axes"], token["reroll_mode"]) == (3, ["quality"], "guaranteed_min")
    [card] = (await session.execute(select(UserCard).where(UserCard.user_id == user.id))).scalars().all()
    # 999 999 demandés, ramenés au maximum possible pour cette combinaison :
    # une légendaire sur cent, ramenée au set de référence de dix, se tire donc
    # sur 1 / (0,01 / 10) = 1 000 — en dessous du plafond de palier (2 000).
    assert card.rarity_id == "legendary"
    assert card.power == 1_000

    out = await messages.build_out(session, msg)
    assert out.reward_items[3].card.id == card.id

    with pytest.raises(HTTPException):
        await messages.claim(session, msg)


async def test_admin_message_rejects_invalid_reward(session):
    await _content(session)
    await make_user(session)
    with pytest.raises(HTTPException):
        await messages.send_admin_broadcast(session, None, "x", "", None, None, [
            {"kind": "reroll", "label": "Vide", "quantity": 1, "rules": {"reroll_mode": "random"}},
        ])
