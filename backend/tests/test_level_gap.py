"""
Écart de niveau maximum entre deux joueurs : calcul de l'écart toléré et refus
des trois transferts (échange, cadeau, achat d'annonce).

Marqués `real_levels` : sans ce marqueur, tous les joueurs sont considérés au
niveau 99 (cf. conftest) et l'écart serait toujours nul.
"""

import pytest
from fastapi import HTTPException

from app.api.players import buy_trade_listing
from app.models.card import UserCard
from app.models.economy import Resource
from app.models.social import TradeListing
from app.services import activities_config, level_gap
from app.services.messages import send_gift
from app.services.trade_requests import create_trade_request
from tests.conftest import make_user

pytestmark = pytest.mark.real_levels

CFG = {"level_gap": {"ratio": 0.30, "min_gap": 5}}


def test_tolerated_gap_follows_the_highest_level():
    assert level_gap.max_gap(CFG, 1) == 5       # plancher : le début de jeu respire
    assert level_gap.max_gap(CFG, 10) == 5      # 30 % de 10 = 3, sous le plancher
    assert level_gap.max_gap(CFG, 20) == 6
    assert level_gap.max_gap(CFG, 40) == 12     # prestige : la tolérance suit
    assert level_gap.ok_of(CFG, 20, 14) and not level_gap.ok_of(CFG, 20, 13)


async def _levelled(session, name: str, level: int):
    """Un joueur au niveau `level` : max_level suffit, le niveau retenu ne baisse jamais."""
    user = await make_user(session, name)
    user.max_level = level
    user.coins = 1_000
    user.gift_policy = user.trade_request_policy = "everyone"
    session.add(user)
    await session.commit()
    return user


async def test_trade_request_refused_beyond_the_gap(session):
    veteran = await _levelled(session, "veteran", 30)
    rookie = await _levelled(session, "rookie", 2)
    neighbour = await _levelled(session, "neighbour", 26)

    with pytest.raises(HTTPException) as exc:
        await create_trade_request(session, veteran, rookie)
    assert exc.value.status_code == 403 and "Écart de niveau" in exc.value.detail

    assert await create_trade_request(session, veteran, neighbour)  # 4 d'écart, 9 tolérés


async def test_gift_refused_beyond_the_gap(session):
    veteran = await _levelled(session, "veteran", 30)
    await _levelled(session, "rookie", 2)
    session.add(Resource(id="dust", name="Poussière"))
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await send_gift(session, veteran, "rookie", "Tiens", "Cadeau", "resource", None, "dust", 100)
    assert exc.value.status_code == 403 and "Écart de niveau" in exc.value.detail


async def test_listing_purchase_refused_beyond_the_gap(session):
    # Acheteur au niveau 8 : les annonces sont débloquées (niveau 7), seul
    # l'écart avec le vendeur doit motiver le refus.
    veteran = await _levelled(session, "veteran", 40)
    rookie = await _levelled(session, "rookie", 8)
    card = UserCard(id="c1", user_id=veteran.id, character_id="x", set_id="s", rarity_id="common",
                    quality_id="fair", specialty_id="normal", jewelry_id="none", power=5)
    session.add_all([card, Resource(id="coins", name="Pièces"),
                     TradeListing(user_id=veteran.id, slot=1, user_card_id=card.id,
                                  resource_id="coins", price=1, mode="buy_now")])
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await buy_trade_listing(veteran.id, 1, rookie, session)
    assert exc.value.status_code == 403 and "Écart de niveau" in exc.value.detail
    assert (await session.get(UserCard, "c1")).user_id == veteran.id


async def test_gap_is_configurable(session):
    await activities_config.save_config(session, {"level_gap": {"ratio": 1.0, "min_gap": 1}})
    veteran = await _levelled(session, "veteran", 30)
    rookie = await _levelled(session, "rookie", 2)
    assert await create_trade_request(session, veteran, rookie)  # tolérance à 100 % : plus de limite
