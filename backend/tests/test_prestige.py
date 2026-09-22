"""
Niveaux de prestige : paliers générés après la fin de la route.
"""

from app.models.level import LevelTier
from app.services import levels
from app.services.wallet import get_balance
from tests.conftest import make_user


async def test_prestige_levels_follow_the_road(session):
    session.add_all([LevelTier(level=1, power_required=0),
                     LevelTier(level=2, power_required=1000, reward_resource_id="coins", reward_amount=100)])
    await session.commit()
    tiers = await levels.get_all_tiers(session)
    p1, p2 = tiers[2], tiers[3]
    assert (p1.level, p1.prestige, p1.power_required, p1.reward_amount) == (3, 1, 1250, 110)
    assert (p2.power_required, p2.reward_amount, p2.bonus_resource_id) == (1563, 120, "frag_legendary")

    user = await make_user(session)
    await levels.claim_level_rewards(session, user)  # puissance 0 : rien à récupérer au-delà du niveau 1
    assert await get_balance(session, user, "frag_legendary") == 0
