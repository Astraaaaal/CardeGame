"""
« Plus ou moins » : on mise ce qui s'échange (jamais les Éclats, achetés en
euros), et le bilan se lit sur les parties elles-mêmes, ressource par ressource.
"""

import pytest
from fastapi import HTTPException

from app.models.activity import HigherLowerGame
from app.models.economy import Resource, UserResource
from app.services import minigames
from app.services.player_stats import higher_lower_record
from tests.conftest import make_user


async def _resources(session):
    session.add_all([
        Resource(id="coins", name="Pièces", tradeable=True, protected=True),
        Resource(id="dust", name="Poussière", tradeable=True),
        Resource(id="gold_nugget", name="Pépite d'or", tradeable=True),
        Resource(id="shards", name="Éclats", tradeable=False, protected=True),
    ])
    await session.commit()


async def test_les_eclats_ne_se_misent_pas(session):
    await _resources(session)
    mises = {r.id for r in await minigames.stake_resources(session)}
    assert "shards" not in mises
    assert {"coins", "dust", "gold_nugget"} <= mises
    # Les pièces passent devant : c'est la mise courante.
    assert (await minigames.stake_resources(session))[0].id == "coins"


async def test_refuse_une_ressource_non_echangeable(session):
    await _resources(session)
    user = await make_user(session)
    with pytest.raises(HTTPException) as exc:
        await minigames.higher_lower_start(session, user, "shards", 50)
    assert exc.value.status_code == 400


@pytest.mark.parametrize("resource_id,mise,accepte", [
    ("coins", 10, False),        # sous le plancher des pièces (50)
    ("coins", 50, True),
    ("gold_nugget", 1, True),    # les ressources rares descendent à 1
    ("gold_nugget", 0, False),
])
async def test_le_plancher_de_mise_depend_de_la_ressource(session, resource_id, mise, accepte):
    await _resources(session)
    user = await make_user(session)
    user.coins = 10_000
    session.add(UserResource(user_id=user.id, resource_id="gold_nugget", amount=100))
    session.add(user)
    await session.commit()
    if accepte:
        # Échoue plus loin (aucune carte à tirer) mais a passé la validation.
        with pytest.raises(Exception) as exc:
            await minigames.higher_lower_start(session, user, resource_id, mise)
        assert "Mise entre" not in str(getattr(exc.value, "detail", ""))
    else:
        with pytest.raises(HTTPException) as exc:
            await minigames.higher_lower_start(session, user, resource_id, mise)
        assert "Mise entre" in exc.value.detail


async def test_le_bilan_se_lit_sur_les_parties(session):
    await _resources(session)
    user = await make_user(session)
    session.add_all([
        HigherLowerGame(user_id=user.id, resource_id="coins", stake=100, status="cashed", payout=250),
        HigherLowerGame(user_id=user.id, resource_id="coins", stake=100, status="lost", payout=0),
        HigherLowerGame(user_id=user.id, resource_id="coins", stake=50, status="lost", payout=0),
        HigherLowerGame(user_id=user.id, resource_id="dust", stake=10, status="cashed", payout=30),
        # En cours : ni gagnée ni perdue, elle ne compte pas encore.
        HigherLowerGame(user_id=user.id, resource_id="coins", stake=999, status="active"),
    ])
    await session.commit()

    bilan = await higher_lower_record(session, user.id)
    assert (bilan["games"], bilan["won_games"]) == (4, 2)
    pieces, poussiere = bilan["by_resource"]
    assert pieces["resource_id"] == "coins"  # les pièces d'abord
    assert (pieces["games"], pieces["won_games"]) == (3, 1)
    assert (pieces["wagered"], pieces["returned"], pieces["net"]) == (250, 250, 0)
    assert (poussiere["wagered"], poussiere["returned"], poussiere["net"]) == (10, 30, 20)


async def test_un_joueur_sans_partie_a_un_bilan_vide(session):
    user = await make_user(session)
    assert await higher_lower_record(session, user.id) == {"games": 0, "won_games": 0, "by_resource": []}
