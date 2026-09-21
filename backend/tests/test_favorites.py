"""
Favoris (catégories nommées et colorées, 10 au plus, par exemplaire) et verrou
anti-recyclage ; un exemplaire qui change de propriétaire perd les deux.
"""

import pytest
from fastapi import HTTPException

from app.api import collection, favorites as fav_api
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import Resource
from app.models.reference import Jewelry, Quality, Rarity, Set, Specialty
from app.schemas.economy import RecycleByIdsRequest
from app.services import favorites
from tests.conftest import make_user


async def _setup(session):
    session.add_all([
        Set(id="s", name="S"), Character(id="c", name="C", type="feu"),
        Rarity(id="common", name="Commune", weight=1, recycle_value=1),
        Quality(id="fair", name="Correcte", weight=1), Specialty(id="normal", name="Normale", weight=1),
        Jewelry(id="none", name="Aucun", weight=1), Resource(id="dust", name="Poussière"),
    ])
    user = await make_user(session, "alice")
    for i in (1, 2):
        session.add(UserCard(id=f"c{i}", user_id=user.id, character_id="c", set_id="s", rarity_id="common",
                             quality_id="fair", specialty_id="normal", jewelry_id="none", power=i))
    await session.commit()
    return user


async def test_categories_colors_and_filter(session):
    user = await _setup(session)
    cats = await fav_api.create_category(fav_api.CategoryBody(name="Top", color="#ff0000"), user, session)
    cats = await fav_api.create_category(fav_api.CategoryBody(name="Deck", color="#00ff00"), user, session)
    top, deck = cats
    await fav_api.add_cards(top["id"], fav_api.CardsBody(card_ids=["c1"]), user, session)
    await fav_api.add_cards(deck["id"], fav_api.CardsBody(card_ids=["c1", "c2"]), user, session)

    res = await collection.get_collection(sort_by="favorite", favorite_id=None, set_id=None, rarity_id=None,
                                          rarity_op="eq", quality_id=None, quality_op="eq", specialty_id=None,
                                          specialty_op="eq", jewelry_id=None, jewelry_op="eq", type_names=[],
                                          min_power=None, max_power=None, user=user, session=session)
    [group] = res.groups
    assert sorted(group.favorite_colors) == ["#00ff00", "#ff0000"] and group.quantity == 2

    filtered = await collection.get_collection(sort_by="rarity", favorite_id=top["id"], set_id=None, rarity_id=None,
                                               rarity_op="eq", quality_id=None, quality_op="eq", specialty_id=None,
                                               specialty_op="eq", jewelry_id=None, jewelry_op="eq", type_names=[],
                                               min_power=None, max_power=None, user=user, session=session)
    assert filtered.groups[0].quantity == 1  # seul c1 est dans « Top »

    for i in range(8):
        await fav_api.create_category(fav_api.CategoryBody(name=f"N{i}", color="#123456"), user, session)
    with pytest.raises(HTTPException):
        await fav_api.create_category(fav_api.CategoryBody(name="Trop", color="#123456"), user, session)


async def test_locked_copy_cannot_be_recycled_and_transfer_releases(session):
    user = await _setup(session)
    await fav_api.lock_cards(fav_api.LockBody(card_ids=["c1"], locked=True), user, session)
    with pytest.raises(HTTPException) as exc:
        await collection.recycle_cards(RecycleByIdsRequest(card_ids=["c1", "c2"]), user, session)
    assert "verrouill" in exc.value.detail

    card = await session.get(UserCard, "c1")
    [cat] = await fav_api.create_category(fav_api.CategoryBody(name="Top", color="#ff0000"), user, session)
    await fav_api.add_cards(cat["id"], fav_api.CardsBody(card_ids=["c1"]), user, session)
    await favorites.release(session, card)
    await session.commit()
    assert card.locked is False
    assert (await fav_api.list_categories(user, session))[0]["count"] == 0
