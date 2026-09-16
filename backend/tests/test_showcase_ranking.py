"""
Vitrine enrichie : meilleur rang global retenu (jamais dégradé), meilleure
série de connexion, achievements affichables seulement s'ils sont débloqués.
"""

from datetime import date, datetime, timedelta

import pytest
from fastapi import HTTPException

from app.api.player import update_showcase
from app.models.achievement import AchievementDef, UserAchievement
from app.models.card import UserCard
from app.schemas.showcase import UpdateShowcaseRequest
from app.services import presence, ranking
from app.services.daily_reward import DailyRewardService
from tests.conftest import make_user


async def _give_power(session, user, power):
    session.add(UserCard(
        user_id=user.id, character_id="c", set_id="s", rarity_id="r",
        quality_id="q", specialty_id="normal", power=power,
    ))
    await session.commit()


async def test_best_rank_keeps_the_best_ever_reached(session):
    alice, bob = await make_user(session, "alice"), await make_user(session, "bob")
    assert await ranking.current_global_rank(session, alice.id) is None

    await _give_power(session, alice, 100)
    await _give_power(session, bob, 50)
    await ranking.refresh_best_rank(session, alice)
    await ranking.refresh_best_rank(session, bob)
    assert (alice.best_global_rank, bob.best_global_rank) == (1, 2)

    # Bob dépasse Alice : Alice descend 2e mais garde son meilleur rang 1.
    await _give_power(session, bob, 200)
    assert await ranking.current_global_rank(session, alice.id) == 2
    await ranking.refresh_best_rank(session, alice)
    await ranking.refresh_best_rank(session, bob)
    assert (alice.best_global_rank, bob.best_global_rank) == (1, 1)


async def test_daily_reward_tracks_best_streak(session):
    user = await make_user(session, "alice")
    user.login_streak = 5
    user.best_login_streak = 5
    user.last_daily_claim = date.today() - timedelta(days=3)  # série cassée
    await session.commit()

    result = await DailyRewardService().check_and_claim(session, user)
    assert result["streak"] == 1
    assert user.best_login_streak == 5


async def test_showcase_only_accepts_unlocked_achievements(session):
    user = await make_user(session, "alice")
    session.add(AchievementDef(id="a1", name="A1", category="meta", metric="level"))
    session.add(AchievementDef(id="a2", name="A2", category="meta", metric="level"))
    session.add(UserAchievement(user_id=user.id, achievement_id="a1"))
    await session.commit()

    with pytest.raises(HTTPException):
        await update_showcase(
            UpdateShowcaseRequest(card_slots=[None, None, None], achievement_slots=["a2", None, None]),
            user=user, session=session,
        )
    with pytest.raises(HTTPException):
        await update_showcase(
            UpdateShowcaseRequest(card_slots=[None, None, None], achievement_slots=["a1", "a1", None]),
            user=user, session=session,
        )

    out = await update_showcase(
        UpdateShowcaseRequest(card_slots=[None, None, None], achievement_slots=[None, "a1", None]),
        user=user, session=session,
    )
    assert [a.id for a in out.achievements] == ["a1"]
    assert out.achievement_slots == [None, "a1", None]


def test_online_threshold_is_about_a_minute():
    user = type("U", (), {})()
    user.last_seen = datetime.utcnow() - timedelta(seconds=45)
    assert presence.is_online(user)
    user.last_seen = datetime.utcnow() - timedelta(seconds=90)
    assert not presence.is_online(user)
