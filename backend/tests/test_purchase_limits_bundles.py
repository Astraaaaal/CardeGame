"""
Limites d'achat réglables (jour / semaine / mois / une fois par compte) et
offres « lot » payées en Éclats.
"""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.api.shop import buy_offer
from app.models.booster import Booster
from app.models.economy import Resource, ShopOffer, ShopPurchase
from app.models.game_config import GameConfig
from app.models.premium import PremiumProduct, PremiumOrder, ORDER_PAID
from app.schemas.economy import ShopBuyRequest
from app.services import booster_inventory, premium, purchase_limits
from app.services.wallet import apply_delta
from tests.conftest import make_user


async def _bundle_offer(session, **fields):
    session.add_all([
        Resource(id="shards", name="Éclats", tradeable=False),
        Booster(id="booster_T", name="Booster test", set_id="s", price=1, resource_id="coins"),
    ])
    offer = ShopOffer(
        id="qa_bundle", kind="bundle", name="Lot QA", description="", resource_id="shards", price=100,
        grants=[{"kind": "resource", "id": "coins", "amount": 1_000}, {"kind": "booster", "id": "booster_T", "amount": 2}],
        **fields,
    )
    session.add(offer)
    await session.commit()
    return offer


async def _tester(session, shards=1_000):
    user = await make_user(session)
    config = GameConfig(id=1, premium_testers=user.username)
    session.add(config)
    await session.commit()
    await apply_delta(session, user, "shards", shards)
    await session.commit()
    return user


async def test_bundle_offer_grants_every_item_and_respects_weekly_limit(session):
    await _bundle_offer(session, limit_period="week", limit_count=2)
    user = await _tester(session)

    res = await buy_offer(ShopBuyRequest(offer_id="qa_bundle"), user, session)
    assert res.new_balance == 900
    assert user.coins == 500 + 1_000
    assert [(o["booster_id"], o["quantity"]) for o in await booster_inventory.list_owned(session, user.id)] \
        == [("booster_T", 2)]

    await buy_offer(ShopBuyRequest(offer_id="qa_bundle"), user, session)
    with pytest.raises(HTTPException) as exc:
        await buy_offer(ShopBuyRequest(offer_id="qa_bundle"), user, session)
    assert exc.value.status_code == 400
    assert "cette semaine" in exc.value.detail

    # Achat de la semaine dernière : ne compte plus dans la limite.
    old = (await session.execute(select(ShopPurchase))).scalars().first()
    old.purchased_at = datetime.utcnow() - timedelta(days=8)
    session.add(old)
    await session.commit()
    await buy_offer(ShopBuyRequest(offer_id="qa_bundle"), user, session)


async def test_bundle_bought_several_times_at_once_counts_each(session):
    await _bundle_offer(session, limit_period="day", limit_count=5)
    user = await _tester(session, shards=1_000)

    await buy_offer(ShopBuyRequest(offer_id="qa_bundle", quantity=3), user, session)
    assert user.coins == 500 + 3_000
    with pytest.raises(HTTPException):
        await buy_offer(ShopBuyRequest(offer_id="qa_bundle", quantity=3), user, session)


async def test_premium_product_limit_period(session):
    user = await make_user(session)
    session.add(GameConfig(id=1, premium_testers=user.username))
    session.add(Resource(id="shards", name="Éclats", tradeable=False))
    session.add(PremiumProduct(
        id="qa_pack", name="Pack QA", price_cents=499, limit_period="month", limit_count=1,
        grants=[{"kind": "resource", "id": "shards", "amount": 550}],
    ))
    await session.commit()

    order = await premium.create_order(session, user, "qa_pack")
    order.status = ORDER_PAID
    order.paid_at = datetime.utcnow()
    session.add(order)
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await premium.create_order(session, user, "qa_pack")
    assert exc.value.status_code == 409
    assert "ce mois" in exc.value.detail

    # Commande payée le mois dernier : la limite se remet à zéro.
    paid = (await session.execute(select(PremiumOrder))).scalars().first()
    paid.paid_at = purchase_limits.window_start("month") - timedelta(days=1)
    session.add(paid)
    await session.commit()
    await premium.create_order(session, user, "qa_pack")
