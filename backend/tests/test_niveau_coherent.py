"""
Le niveau doit être le MÊME partout. Il se calcule sur les contributions
plafonnées (cf. levels.LEVEL_CONTRIBUTION_CAP), jamais sur la puissance brute :
la fiche de statistiques annonçait sinon un niveau que les déblocages, le
classement et la vitrine ne reconnaissaient pas.
"""

import pytest

from app.models.card import UserCard
from app.models.level import LevelTier
from app.services import unlocks
from app.services.levels import LEVEL_CONTRIBUTION_CAP
from app.services.player_stats import build_player_stats
from app.services.showcase_view import build_showcase_response
from tests.conftest import make_user

pytestmark = pytest.mark.real_levels


def _carte(user_id, cid, power):
    return UserCard(id=cid, user_id=user_id, character_id="c", set_id="s", rarity_id="common",
                    quality_id="fair", specialty_id="normal", jewelry_id="none",
                    drop_probability=0.05, power=power)


async def test_le_niveau_de_la_fiche_suit_les_contributions_plafonnees(session):
    session.add_all([LevelTier(level=lvl, power_required=req) for lvl, req in
                     [(1, 0), (2, 100), (3, 200), (5, 400), (10, 1_000), (20, 2_000)]])
    await session.commit()
    user = await make_user(session)

    # Deux cartes très puissantes : 4 000 de puissance brute, mais seulement
    # 2 × 150 = 300 de contribution au niveau.
    session.add_all([_carte(user.id, "a", 2_000), _carte(user.id, "b", 2_000)])
    await session.commit()

    stats = await build_player_stats(session, user)
    assert stats["total_power"] == 4_000        # la puissance affichée reste entière
    assert stats["current_level"] == 3          # 300 de contribution → niveau 3
    # Et c'est bien le niveau dont dépend le reste du jeu.
    assert await unlocks.level_of(session, user) == stats["current_level"]


async def test_la_fiche_et_la_vitrine_annoncent_le_meme_niveau(session):
    session.add_all([LevelTier(level=lvl, power_required=req) for lvl, req in
                     [(1, 0), (2, 100), (3, 200), (5, 400), (10, 1_000)]])
    await session.commit()
    user = await make_user(session)
    session.add_all([_carte(user.id, f"c{i}", LEVEL_CONTRIBUTION_CAP * 3) for i in range(4)])
    await session.commit()

    stats = await build_player_stats(session, user)
    vitrine = await build_showcase_response(session, user, user.id)
    assert stats["current_level"] == vitrine.level
