"""
Déblocages par niveau (plus haut niveau atteint, définitif) et taxe sur les
transferts (sur ce qu'on reçoit, taux selon le plus haut niveau des deux).
"""

import pytest
from fastapi import HTTPException

from app.models.card import UserCard
from app.models.level import LevelTier
from app.services import activities_config, trade_tax, unlocks
from app.services.levels import LEVEL_CONTRIBUTION_CAP
from tests.conftest import make_user

pytestmark = pytest.mark.real_levels


async def _tiers(session):
    session.add_all([LevelTier(level=lvl, power_required=req) for lvl, req in
                     [(1, 0), (2, 100), (3, 200), (4, 300), (5, 400), (6, 500), (10, 1000), (20, 2000)]])
    await session.commit()


def _card(user_id, cid, power, prob=0.05, rarity="common"):
    return UserCard(id=cid, user_id=user_id, character_id="c", set_id="s", rarity_id=rarity, quality_id="fair",
                    specialty_id="normal", jewelry_id="none", drop_probability=prob, power=power)


def _cards(user_id, prefix, count):
    """Une collection qui atteint un niveau donné. Chaque carte apporte au plus
    LEVEL_CONTRIBUTION_CAP au niveau : on monte en collectionnant, pas sur un
    seul tirage chanceux."""
    return [_card(user_id, f"{prefix}{i}", LEVEL_CONTRIBUTION_CAP) for i in range(count)]


async def test_features_unlock_by_highest_level_ever_reached(session):
    await _tiers(session)
    user = await make_user(session)
    with pytest.raises(HTTPException) as exc:
        await unlocks.require(session, user, "trades")
    assert exc.value.status_code == 403 and "niveau 5" in exc.value.detail

    cards = _cards(user.id, "big", 3)  # 3 × 150 = 450 de contribution → niveau 5
    session.add_all(cards)
    await session.commit()
    await unlocks.require(session, user, "trades")  # niveau 5 atteint
    assert user.max_level == 5

    for card in cards:  # la puissance retombe
        await session.delete(card)
    await session.commit()
    await unlocks.require(session, user, "trades")  # reste débloqué
    status = await unlocks.status(session, user)
    assert status["level"] == 5 and status["features"]["machine"] == {"label": "Machine d'amélioration", "level": 8, "unlocked": False}


async def test_progressions_follow_level(session):
    cfg = await activities_config.get_config(session)
    assert [unlocks.expedition_slots(cfg, lvl) for lvl in (2, 3, 9, 14)] == [0, 1, 2, 3]
    # Verrouillé avant son niveau, puis croissant jusqu'à son plafond (1,5).
    assert unlocks.presence_max_multiplier(cfg, 4) == 1.0
    assert unlocks.presence_max_multiplier(cfg, 5) == 1.2
    assert unlocks.presence_max_multiplier(cfg, 20) == 1.5
    assert unlocks.higher_lower_max_stake(cfg, 7) == 0  # avant son niveau de déblocage
    assert unlocks.higher_lower_max_stake(cfg, 8) == 500 and unlocks.higher_lower_max_stake(cfg, 30) == 5000
    assert unlocks.workshop_gauges(cfg, 2) == 10 and unlocks.workshop_gauges(cfg, 3) == 12
    assert [unlocks.converter_uses(cfg, lvl) for lvl in (6, 7, 12, 17)] == [0, 1, 2, 3]


async def test_card_value_and_rate(session):
    await _tiers(session)
    cfg = await activities_config.get_config(session)
    # Les deux repères de l'échelle (cf. le module) : une commune sans intérêt
    # ne coûte presque rien, une légendaire moyenne vaut autour de mille.
    weak_common = _card(1, "a", 1, prob=0.25)  # « 1 sur 4 » à 1 de puissance
    assert trade_tax.card_value(cfg, weak_common) < 3
    legendary = _card(1, "b", 409, prob=1 / 818, rarity="legendary")
    assert 900 < trade_tax.card_value(cfg, legendary) < 1300

    low, high = await make_user(session, "low"), await make_user(session, "high")
    session.add_all(_cards(high.id, "h", 14))  # 14 × 150 = 2 100 → niveau 20
    await session.commit()
    assert await trade_tax.rate_for(session, low) == 0.05
    assert await trade_tax.rate_for(session, low, high) == 0.2  # 5 % + 15 niveaux × 1 %
    assert await trade_tax.tax_for_items(session, 0.05, [{"type": "card", "card": weak_common}]) == 1  # 1 pièce minimum
    assert await trade_tax.tax_for_items(session, 0.1, [{"type": "resource", "resource_id": "coins", "amount": 1000}]) == 100


async def test_gift_claim_needs_coins_for_the_tax(session):
    from app.models.message import Message
    from app.services import messages
    await _tiers(session)
    sender, recipient = await make_user(session, "sender"), await make_user(session, "recipient")
    session.add(_card(sender.id, "gift", 300, prob=1 / 800, rarity="legendary"))
    recipient.coins = 0
    msg = Message(sender_type="player", sender_user_id=sender.id, recipient_user_id=recipient.id,
                  subject="Cadeau", body="", reward_card_id="gift")
    session.add_all([recipient, msg])
    await session.commit()

    tax = await messages.gift_tax(session, msg)
    assert tax > 0
    with pytest.raises(HTTPException) as exc:
        await messages.claim(session, msg)
    assert "taxe" in exc.value.detail
    recipient.coins = tax
    session.add(recipient)
    await session.commit()
    await messages.claim(session, msg)
    assert recipient.coins == 0 and (await session.get(UserCard, "gift")).user_id == recipient.id
