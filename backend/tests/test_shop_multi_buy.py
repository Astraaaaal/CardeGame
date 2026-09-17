"""
Boutique à ressources : achat ×N (limite du jour et solde vérifiés pour le
total) et rerolls gardés en inventaire avec leurs règles figées à l'achat.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import func, select

from app.api.shop import buy_offer, list_reroll_tokens, use_reroll_token
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import ShopOffer, ShopPurchase
from app.schemas.economy import ShopBuyRequest, RerollUseRequest
from tests.conftest import make_user


async def _offer(session, **fields):
    offer = ShopOffer(resource_id="coins", description="", **fields)
    session.add(offer)
    await session.commit()
    return offer


async def _card_offer(session, price=50, limit=None):
    session.add(Character(id="pika", name="Pika", type="electric"))
    return await _offer(
        session, id="card_pika", kind="specific_card", name="Pika garanti", price=price,
        purchase_limit_per_day=limit, character_id="pika", rarity_id="rare",
        quality_id="mint", specialty_id="normal", jewelry_id="none",
    )


async def _purchases(session, user):
    return (await session.execute(
        select(func.count()).select_from(ShopPurchase).where(ShopPurchase.user_id == user.id)
    )).scalar_one()


async def test_buy_specific_card_by_five_charges_total_and_counts_five_purchases(session):
    user = await make_user(session)
    await _card_offer(session, price=50)

    res = await buy_offer(ShopBuyRequest(offer_id="card_pika", quantity=5), user, session)

    assert len(res.cards) == 5
    assert user.coins == 500 - 250
    assert user.total_cards == 5
    assert await _purchases(session, user) == 5


async def test_buy_by_five_refused_when_daily_limit_leaves_less(session):
    user = await make_user(session)
    await _card_offer(session, price=10, limit=3)

    with pytest.raises(HTTPException) as exc:
        await buy_offer(ShopBuyRequest(offer_id="card_pika", quantity=5), user, session)
    assert exc.value.status_code == 400
    assert user.coins == 500

    await buy_offer(ShopBuyRequest(offer_id="card_pika", quantity=3), user, session)
    assert await _purchases(session, user) == 3


async def test_buy_by_ten_refused_without_enough_for_the_total(session):
    user = await make_user(session)
    await _card_offer(session, price=60)

    with pytest.raises(HTTPException) as exc:
        await buy_offer(ShopBuyRequest(offer_id="card_pika", quantity=10), user, session)
    assert exc.value.status_code == 400
    assert user.total_cards == 0


async def test_immediate_reroll_cannot_be_bought_by_several(session):
    user = await make_user(session)
    await _offer(session, id="rr", kind="reroll", name="Reroll", price=10, reroll_power=True, reroll_mode="random")

    with pytest.raises(HTTPException) as exc:
        await buy_offer(ShopBuyRequest(offer_id="rr", card_id="x", quantity=5), user, session)
    assert exc.value.status_code == 400


async def test_reroll_tokens_keep_purchase_rules_and_are_consumed_on_use(session):
    user = await make_user(session)
    other = await make_user(session, "other")
    offer = await _offer(session, id="rr", kind="reroll", name="Reroll puissance", price=20,
                         reroll_power=True, reroll_mode="random")

    await buy_offer(ShopBuyRequest(offer_id="rr", to_inventory=True, quantity=3), user, session)
    assert user.coins == 500 - 60

    # L'admin change l'offre après l'achat : le stock garde les règles d'origine.
    offer.reroll_power = False
    offer.reroll_rarity = True
    session.add(offer)
    await session.commit()

    [token] = await list_reroll_tokens(session, user)
    assert (token["quantity"], token["axes"], token["reroll_power"]) == (3, [], True)

    card = UserCard(user_id=user.id, character_id="pika", set_id="s", rarity_id="rare",
                    quality_id="mint", specialty_id="normal", jewelry_id="none")
    foreign = UserCard(user_id=other.id, character_id="pika", set_id="s", rarity_id="rare",
                       quality_id="mint", specialty_id="normal", jewelry_id="none")
    session.add_all([card, foreign])
    await session.commit()

    res = await use_reroll_token(token["id"], RerollUseRequest(card_id=card.id), session, user)
    assert res["card"].rarity_id == "rare"  # seule la puissance est relancée
    assert res["token"]["quantity"] == 2

    with pytest.raises(HTTPException) as exc:
        await use_reroll_token(token["id"], RerollUseRequest(card_id=foreign.id), session, user)
    assert exc.value.status_code == 404

    for _ in range(2):
        await use_reroll_token(token["id"], RerollUseRequest(card_id=card.id), session, user)
    with pytest.raises(HTTPException) as exc:
        await use_reroll_token(token["id"], RerollUseRequest(card_id=card.id), session, user)
    assert exc.value.status_code == 400
    assert await list_reroll_tokens(session, user) == []
