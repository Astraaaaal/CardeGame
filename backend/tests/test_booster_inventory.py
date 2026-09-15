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
