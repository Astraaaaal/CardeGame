"""
Nouvelles métriques : rerolls (compteurs, quête), achats en boutique,
classement (top N), complétion de collection, combinaison spécialité + bijou,
et statistiques du joueur correspondantes.
"""

from app.models.achievement import AchievementDef
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import ShopPurchase
from app.services import activity, quest_progress
from app.services.achievements import evaluate_metric
from app.services.player_stats import build_player_stats
from tests.conftest import make_user


def _def(metric, param=None):
    return AchievementDef(id="x", name="x", category="meta", metric=metric, threshold=1, metric_param=param)


def _card(user, **kw):
    base = dict(user_id=user.id, character_id="c1", set_id="s", rarity_id="common",
                quality_id="fair", specialty_id="normal", jewelry_id="none")
    return UserCard(**{**base, **kw})


async def test_track_reroll_counts_uses_and_rarity_upgrades(session):
    user = await make_user(session)
    card = _card(user, rarity_id="epic")
    session.add(card)
    await session.commit()

    await activity.track_reroll(session, user, "common", card)
    await activity.track_reroll(session, user, "legendary", card)
    await session.commit()

    assert (user.rerolls_used, user.reroll_rarity_upgrades) == (2, 1)
    assert await evaluate_metric(session, user, _def("rerolls_used")) == 2
    assert await quest_progress.get_count(
        session, user.id, "rerolls_used", "daily", quest_progress.daily_key(),
    ) == 2
    assert await quest_progress.get_count(
        session, user.id, "rare_cards_obtained", "daily", quest_progress.daily_key(),
    ) == 1


async def test_rank_completion_and_combo_metrics(session):
    user = await make_user(session)
    session.add_all([Character(id="c1", name="A", type="t"), Character(id="c2", name="B", type="t")])
    session.add(_card(user, specialty_id="shiny", jewelry_id="prismatic", rarity_id="legendary"))
    session.add(ShopPurchase(user_id=user.id, offer_id="o"))
    user.best_global_rank = 3
    session.add(user)
    await session.commit()

    assert await evaluate_metric(session, user, _def("rank_reached", "3")) == 1
    assert await evaluate_metric(session, user, _def("rank_reached", "1")) == 0
    assert await evaluate_metric(session, user, _def("collection_completion_pct")) == 50
    assert await evaluate_metric(session, user, _def("rarity_count", "legendary")) == 1
    assert await evaluate_metric(session, user, _def("specialty_jewelry_owned", "shiny:prismatic")) == 1
    assert await evaluate_metric(session, user, _def("shop_purchases")) == 1

    stats = await build_player_stats(session, user)
    assert (stats["characters_owned"], stats["characters_total"], stats["shop_purchases"]) == (1, 2, 1)
