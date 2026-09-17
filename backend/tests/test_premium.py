"""
Boutique premium (app/services/premium.py, stripe_client.py) : accès fermé
sauf testeurs, commandes créditées une seule fois, offre « une fois par
compte », signature des webhooks Stripe, monnaie premium non échangeable.
"""

import hashlib
import hmac
import time

import pytest
from fastapi import HTTPException

from app.api.shop import buy_offer
from app.models.economy import Resource, ShopOffer
from app.models.game_config import GameConfig
from app.models.premium import Cosmetic, PremiumProduct, UserCosmetic
from app.schemas.economy import ShopBuyRequest
from app.services import premium, stripe_client
from app.services import trade_session as ts
from app.services.wallet import apply_delta, get_balance
from tests.conftest import make_user


async def _setup(session, enabled=False, testers=""):
    session.add(GameConfig(id=1, premium_shop_enabled=enabled, premium_testers=testers))
    session.add(Resource(id="shards", name="Éclats", protected=True, tradeable=False))
    session.add(Cosmetic(id="aurora", kind="avatar_frame", name="Aurore"))
    await session.commit()


async def test_access_is_closed_except_for_testers(session):
    await _setup(session, enabled=False, testers="Alice, bob")
    alice, carol = await make_user(session, "alice"), await make_user(session, "carol")
    assert await premium.has_access(session, alice)
    assert not await premium.has_access(session, carol)

    config = await session.get(GameConfig, 1)
    config.premium_shop_enabled = True
    await session.commit()
    assert await premium.has_access(session, carol)


async def test_paid_order_is_credited_once_and_once_per_account_is_enforced(session):
    await _setup(session, testers="alice")
    alice = await make_user(session, "alice")
    session.add(PremiumProduct(
        id="starter", name="Pack de démarrage", price_cents=299, once_per_account=True,
        grants=[{"kind": "resource", "id": "shards", "amount": 500}, {"kind": "cosmetic", "id": "aurora", "amount": 1}],
    ))
    await session.commit()

    order = await premium.create_order(session, alice, "starter")
    assert await premium.fulfill_order(session, order.id, None, 299, "eur")
    assert not await premium.fulfill_order(session, order.id, None, 299, "eur")  # webhook rejoué

    assert await get_balance(session, alice, "shards") == 500
    assert await session.get(UserCosmetic, (alice.id, "aurora"))
    with pytest.raises(HTTPException) as exc:
        await premium.create_order(session, alice, "starter")
    assert exc.value.status_code == 409


async def test_orders_are_refused_while_shop_is_closed(session):
    await _setup(session)
    carol = await make_user(session, "carol")
    session.add(PremiumProduct(id="p", name="P", price_cents=99, grants=[{"kind": "resource", "id": "shards", "amount": 1}]))
    await session.commit()
    with pytest.raises(HTTPException) as exc:
        await premium.create_order(session, carol, "p")
    assert exc.value.status_code == 403


def test_webhook_signature():
    payload, secret, now = b'{"id":"evt"}', "whsec_test", time.time()
    good = hmac.new(secret.encode(), f"{int(now)}.".encode() + payload, hashlib.sha256).hexdigest()
    header = f"t={int(now)},v1={good}"
    assert stripe_client.verify_webhook_signature(payload, header, secret, now=now)
    assert not stripe_client.verify_webhook_signature(payload + b" ", header, secret, now=now)
    assert not stripe_client.verify_webhook_signature(payload, header, "autre_secret", now=now)
    assert not stripe_client.verify_webhook_signature(payload, header, secret, now=now + 3600)  # rejeu tardif


async def test_premium_currency_cannot_be_traded(session):
    await _setup(session)
    alice, bob = await make_user(session, "alice"), await make_user(session, "bob")
    await apply_delta(session, alice, "shards", 100)
    await session.commit()
    trade = await ts.create_session(session, alice.id, bob.id)
    with pytest.raises(HTTPException) as exc:
        await ts.add_resource_item(session, trade, alice.id, "shards", 10)
    assert exc.value.status_code == 400


async def test_cosmetic_offer_in_shards_requires_access_and_unlocks_once(session):
    await _setup(session)
    alice = await make_user(session, "alice")
    await apply_delta(session, alice, "shards", 50)
    session.add(ShopOffer(id="frame", kind="cosmetic", name="Cadre Aurore", resource_id="shards", price=10, cosmetic_id="aurora"))
    await session.commit()

    with pytest.raises(HTTPException) as exc:
        await buy_offer(ShopBuyRequest(offer_id="frame"), user=alice, session=session)
    assert exc.value.status_code == 403  # boutique fermée

    config = await session.get(GameConfig, 1)
    config.premium_testers = "alice"
    await session.commit()
    await buy_offer(ShopBuyRequest(offer_id="frame"), user=alice, session=session)
    assert await session.get(UserCosmetic, (alice.id, "aurora"))
    assert await get_balance(session, alice, "shards") == 40
    with pytest.raises(HTTPException) as exc:
        await buy_offer(ShopBuyRequest(offer_id="frame"), user=alice, session=session)
    assert exc.value.status_code == 409


async def test_stripe_webhook_route_credits_order_once(session, monkeypatch):
    import json as _json
    import httpx
    from app.config import settings
    from app.database import get_session
    from app.main import app

    await _setup(session, testers="alice")
    alice = await make_user(session, "alice")
    session.add(PremiumProduct(id="p500", name="500 éclats", price_cents=499, grants=[{"kind": "resource", "id": "shards", "amount": 500}]))
    await session.commit()
    order = await premium.create_order(session, alice, "p500")
    order.stripe_session_id = "cs_test_123"
    await session.commit()

    monkeypatch.setattr(settings, "STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", "whsec_x")

    async def _session_override():
        yield session
    app.dependency_overrides[get_session] = _session_override
    try:
        body = _json.dumps({"type": "checkout.session.completed", "data": {"object": {
            "id": "cs_test_123", "payment_status": "paid", "amount_total": 499, "currency": "eur",
            "metadata": {"order_id": str(order.id)},
        }}}).encode()
        ts_now = int(time.time())
        sig = hmac.new(b"whsec_x", f"{ts_now}.".encode() + body, hashlib.sha256).hexdigest()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            bad = await client.post("/api/premium/stripe-webhook", content=body, headers={"stripe-signature": f"t={ts_now},v1=deadbeef"})
            assert bad.status_code == 400
            for _ in range(2):  # Stripe peut renvoyer le même événement
                res = await client.post("/api/premium/stripe-webhook", content=body, headers={"stripe-signature": f"t={ts_now},v1={sig}"})
                assert res.status_code == 200
    finally:
        app.dependency_overrides.clear()

    await session.refresh(order)
    assert order.status == "paid"
    assert await get_balance(session, alice, "shards") == 500


async def test_wrong_amount_is_not_credited_and_expired_or_refunded_orders_change_status(session):
    await _setup(session, testers="alice")
    alice = await make_user(session, "alice")
    session.add(PremiumProduct(id="p500", name="500 éclats", price_cents=499, grants=[{"kind": "resource", "id": "shards", "amount": 500}]))
    await session.commit()

    order = await premium.create_order(session, alice, "p500")
    assert not await premium.fulfill_order(session, order.id, None, 1, "eur")
    assert not await premium.fulfill_order(session, order.id, None, 499, "usd")
    assert await get_balance(session, alice, "shards") == 0
    assert await premium.expire_order(session, order.id)
    assert not await premium.fulfill_order(session, order.id, None, 499, "eur")  # expirée : plus créditable

    paid = await premium.create_order(session, alice, "p500")
    assert await premium.fulfill_order(session, paid.id, None, 499, "eur")
    assert not await premium.expire_order(session, paid.id)
    assert await premium.refund_order(session, paid.id)
    await session.refresh(paid)
    assert paid.status == "refunded"
