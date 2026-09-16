"""
Quêtes (app/services/quests.py) — deux garanties critiques :
1. Une quête ne peut pas être récupérée deux fois (même bug qu'on a eu sur
   les achievements : claim_quest() doit renvoyer l'état à jour sans jamais
   permettre un second crédit).
2. Une récompense "booster" (reward_booster_id) doit bien créditer
   l'inventaire du joueur, au même titre qu'une récompense en ressource.
"""

import pytest
from fastapi import HTTPException

from app.models.quest import QuestDef, UserQuest
from app.models.booster_inventory import UserBoosterInventory
from app.services import quests, quest_progress
from tests.conftest import make_user


async def _make_quest_def(session, **overrides) -> QuestDef:
    defaults = dict(
        id="q_test", name="Quête de test", description="", period="daily",
        metric="packs_opened", threshold=3,
    )
    defaults.update(overrides)
    qdef = QuestDef(**defaults)
    session.add(qdef)
    await session.commit()
    return qdef


async def _assign_and_complete(session, user, qdef: QuestDef) -> UserQuest:
    uq = UserQuest(user_id=user.id, quest_def_id=qdef.id, period="daily", period_key=quest_progress.daily_key())
    session.add(uq)
    await quest_progress.increment(session, user.id, qdef.metric, qdef.threshold)
    await session.commit()
    await session.refresh(uq)
    return uq


async def test_claim_grants_resource_reward_and_is_idempotent(session):
    user = await make_user(session)
    qdef = await _make_quest_def(session, reward_resource_id="coins", reward_amount=100)
    uq = await _assign_and_complete(session, user, qdef)

    result = await quests.claim_quest(session, user, uq.id)

    assert result["claimed_at"] is not None
    assert user.coins == 600  # 500 de base + 100 de récompense

    with pytest.raises(HTTPException) as exc_info:
        await quests.claim_quest(session, user, uq.id)
    assert exc_info.value.status_code == 409
    assert user.coins == 600  # pas de second crédit


async def test_claim_grants_booster_reward(session):
    user = await make_user(session)
    qdef = await _make_quest_def(session, id="q_booster", reward_booster_id="booster_A1")
    uq = await _assign_and_complete(session, user, qdef)

    result = await quests.claim_quest(session, user, uq.id)

    assert result["reward_booster_id"] == "booster_A1"
    row = await session.get(UserBoosterInventory, (user.id, "booster_A1"))
    assert row is not None
    assert row.quantity == 1


async def test_claim_before_threshold_reached_fails(session):
    user = await make_user(session)
    qdef = await _make_quest_def(session, threshold=3)
    uq = UserQuest(user_id=user.id, quest_def_id=qdef.id, period="daily", period_key=quest_progress.daily_key())
    session.add(uq)
    await quest_progress.increment(session, user.id, qdef.metric, 1)  # sous le seuil
    await session.commit()
    await session.refresh(uq)

    with pytest.raises(HTTPException) as exc_info:
        await quests.claim_quest(session, user, uq.id)
    assert exc_info.value.status_code == 400
