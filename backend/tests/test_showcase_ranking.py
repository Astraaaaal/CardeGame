"""
Vitrine enrichie : meilleur rang global retenu (jamais dégradé), meilleure
série de connexion, achievements affichables seulement s'ils sont débloqués.
"""

from datetime import date, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlmodel import select

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
    alice, bob, carol = [await make_user(session, n) for n in ("alice", "bob", "carol")]
    assert await ranking.current_global_rank(session, alice.id) is None

    await _give_power(session, alice, 100)
    await _give_power(session, bob, 50)
    await _give_power(session, carol, 50)
    await ranking.refresh_all_best_ranks(session)
    # Ex-aequo : même rang, le suivant saute.
    assert (alice.best_global_rank, bob.best_global_rank, carol.best_global_rank) == (1, 2, 2)

    # Bob dépasse Alice : Alice descend 2e mais garde son meilleur rang 1,
    # et Bob obtient le 1er rang sans avoir eu besoin de consulter quoi que ce soit.
    await _give_power(session, bob, 200)
    assert await ranking.current_global_rank(session, alice.id) == 2
    await ranking.refresh_all_best_ranks(session)
    assert (alice.best_global_rank, bob.best_global_rank, carol.best_global_rank) == (1, 1, 2)


async def test_rank_improves_when_someone_else_loses_power(session):
    alice, bob = await make_user(session, "alice"), await make_user(session, "bob")
    await _give_power(session, alice, 100)
    await _give_power(session, bob, 50)
    await ranking.refresh_all_best_ranks(session)
    assert bob.best_global_rank == 2

    # Alice recycle toutes ses cartes : Bob passe 1er sans rien faire lui-même.
    for card in (await session.execute(select(UserCard).where(UserCard.user_id == alice.id))).scalars().all():
        await session.delete(card)
    await session.commit()
    await ranking.refresh_all_best_ranks(session)
    assert bob.best_global_rank == 1


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


def test_online_threshold_is_thirty_seconds():
    user = type("U", (), {})()
    user.last_seen = datetime.utcnow() - timedelta(seconds=20)
    assert presence.is_online(user)
    user.last_seen = datetime.utcnow() - timedelta(seconds=40)
    assert not presence.is_online(user)
