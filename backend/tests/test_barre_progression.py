"""
La barre de progression se remplit ENTRE le seuil du niveau atteint et celui
du suivant. Mesurée depuis zéro, elle restait presque pleine en permanence :
à 90 000 de puissance sur un palier 14 à 98 000, elle affichait 92 % alors
qu'on venait tout juste d'entrer dans le niveau 13.
"""

import pytest

from app.models.card import UserCard
from app.models.level import LevelTier
from app.services import levels
from tests.conftest import make_user

pytestmark = pytest.mark.real_levels

PALIERS = [(1, 0), (12, 71_800), (13, 84_000), (14, 98_000)]


def _cartes(user_id, total):
    """Des cartes plafonnées qui totalisent `total` de contribution."""
    plein, reste = divmod(total, levels.LEVEL_CONTRIBUTION_CAP)
    puissances = [levels.LEVEL_CONTRIBUTION_CAP] * plein + ([reste] if reste else [])
    return [
        UserCard(id=f"c{i}", user_id=user_id, character_id="c", set_id="s", rarity_id="common",
                 quality_id="fair", specialty_id="normal", jewelry_id="none",
                 drop_probability=0.05, power=p)
        for i, p in enumerate(puissances)
    ]


async def _statut(session, total):
    session.add_all([LevelTier(level=lvl, power_required=req) for lvl, req in PALIERS])
    await session.commit()
    user = await make_user(session)
    session.add_all(_cartes(user.id, total))
    await session.commit()
    return await levels.get_status(session, user)


def _pourcentage(statut) -> int:
    depart = statut["current_level_power_required"]
    restant = statut["next_level_power_required"] - depart
    return round((statut["total_power"] - depart) / restant * 100)


async def test_le_seuil_du_niveau_atteint_est_expose(session):
    statut = await _statut(session, 90_000)
    assert statut["current_level"] == 13
    assert statut["current_level_power_required"] == 84_000
    assert statut["next_level_power_required"] == 98_000
    # 6 000 parcourus sur les 14 000 du palier : 43 %, et non 92 %.
    assert _pourcentage(statut) == 43


async def test_la_barre_repart_a_zero_a_chaque_palier(session):
    statut = await _statut(session, 84_000)  # pile à l'entrée du niveau 13
    assert statut["current_level"] == 13
    assert _pourcentage(statut) == 0


async def test_la_barre_est_pleine_juste_avant_le_palier(session):
    statut = await _statut(session, 97_950)
    assert statut["current_level"] == 13
    assert _pourcentage(statut) == 100
