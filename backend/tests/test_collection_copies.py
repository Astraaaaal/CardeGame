"""
Collection : le détail des exemplaires (`with_copies`) joint à chaque groupe —
base du mode recyclage, où l'on sélectionne des exemplaires précis.
"""

from app.api.collection import get_collection
from app.models.card import UserCard
from app.models.character import Character
from app.models.favorite import FavoriteCard, FavoriteCategory
from app.models.reference import Jewelry, Quality, Rarity, Set, Specialty
from tests.conftest import make_user


# La route est appelée directement : ses valeurs par défaut sont des Query()
# que FastAPI résoudrait normalement, il faut donc les donner ici.
DEFAULTS = dict(
    sort_by="rarity", favorite_id=None, set_id=None,
    rarity_id=None, rarity_op="eq", quality_id=None, quality_op="eq",
    specialty_id=None, specialty_op="eq", jewelry_id=None, jewelry_op="eq",
    type_names=[], min_power=None, max_power=None, with_copies=False,
)


async def _collection(session, user, **kwargs):
    return await get_collection(user=user, session=session, **{**DEFAULTS, **kwargs})


async def _reference(session):
    session.add_all([
        Character(id="c", name="Perso", type="feu"), Set(id="s", name="Set"),
        Rarity(id="common", name="Commune", weight=1), Quality(id="fair", name="Correcte", weight=1),
        Specialty(id="normal", name="Normale", weight=1), Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()


async def _card(session, user, card_id: str, power: int, locked: bool = False):
    card = UserCard(id=card_id, user_id=user.id, character_id="c", set_id="s", rarity_id="common",
                    quality_id="fair", specialty_id="normal", jewelry_id="none",
                    power=power, locked=locked, drop_probability=0.01)
    session.add(card)
    await session.commit()
    return card


async def test_copies_are_omitted_by_default(session):
    user = await make_user(session)
    await _reference(session)
    await _card(session, user, "a", 10)

    response = await _collection(session, user)
    assert response.groups[0].quantity == 1 and response.groups[0].copies == []


async def test_copies_are_sorted_by_power_with_lock_and_favorites(session):
    user = await make_user(session)
    await _reference(session)
    await _card(session, user, "faible", 10)
    await _card(session, user, "fort", 900)
    await _card(session, user, "verrou", 500, locked=True)
    category = FavoriteCategory(user_id=user.id, name="Top", color="#fff")
    session.add(category)
    await session.commit()
    session.add(FavoriteCard(category_id=category.id, user_card_id="fort"))
    await session.commit()

    group = (await _collection(session, user, with_copies=True)).groups[0]
    assert [c.id for c in group.copies] == ["fort", "verrou", "faible"]
    assert group.copies[0].favorite_ids == [category.id]
    assert group.copies[1].locked and not group.copies[2].locked


async def test_copies_follow_the_power_filter(session):
    """Le filtre de puissance porte sur chaque exemplaire : le mode recyclage ne
    peut donc pas sélectionner une carte que l'affichage a écartée."""
    user = await make_user(session)
    await _reference(session)
    await _card(session, user, "faible", 10)
    await _card(session, user, "fort", 900)

    group = (await _collection(session, user, with_copies=True, max_power=100)).groups[0]
    assert [c.id for c in group.copies] == ["faible"] and group.quantity == 1
