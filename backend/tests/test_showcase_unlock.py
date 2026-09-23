"""
La vitrine s'ouvre au niveau 3 : une vitrine vide au premier lancement dessert
le jeu — on y entre quand on a enfin de quoi exposer.
"""

import pytest
from fastapi import HTTPException

from app.services import unlocks
from tests.conftest import make_user


@pytest.mark.real_levels
@pytest.mark.asyncio
async def test_la_vitrine_est_fermee_au_niveau_1(session):
    user = await make_user(session)
    user.max_level = 1
    with pytest.raises(HTTPException) as erreur:
        await unlocks.require(session, user, "showcase")
    assert erreur.value.status_code == 403
    assert "niveau 3" in erreur.value.detail


@pytest.mark.real_levels
@pytest.mark.asyncio
async def test_la_vitrine_s_ouvre_au_niveau_3(session):
    user = await make_user(session)
    user.max_level = 3
    await unlocks.require(session, user, "showcase")  # ne lève pas


@pytest.mark.asyncio
async def test_le_libelle_est_lisible_dans_le_message(session):
    """Le joueur doit lire « Vitrine », pas « showcase »."""
    assert unlocks.FEATURE_LABELS["showcase"] == "Vitrine"
