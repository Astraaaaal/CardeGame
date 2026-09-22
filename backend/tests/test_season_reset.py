"""
Fin de bêta : remise à zéro des comptes (on garde compte, réglages et amis)
et jeu fermé (connexion refusée sauf à l'admin).
"""

import pytest
from fastapi import HTTPException

from app.config import settings
from app.models.activity import UserActivity
from app.models.booster_inventory import UserBoosterInventory
from app.models.card import UserCard
from app.models.favorite import FavoriteCategory
from app.models.economy import Resource, UserResource
from app.models.game_config import GameConfig
from app.models.social import FriendRequest
from app.models.token import RefreshToken
from app.models.user import User
from app.services import game_status, guilds, season_reset
from tests.conftest import make_user


async def test_reset_keeps_accounts_and_friends_but_wipes_progress(session):
    session.add_all([
        Resource(id="coins", name="Pièces", starting_amount=300),
        Resource(id="dust", name="Poussière", starting_amount=50),
    ])
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    carol = await make_user(session, "carol")
    alice.coins, alice.packs_opened, alice.gift_policy = 9_999, 12, "everyone"
    # Nouveautés : prestige (niveau au-delà de la route), meilleur rang, niveau max.
    alice.claimed_level, alice.max_level, alice.best_global_rank = 23, 23, 1
    session.add_all([
        alice,
        FriendRequest(requester_id=alice.id, addressee_id=bob.id, status="accepted"),
        FriendRequest(requester_id=carol.id, addressee_id=alice.id, status="pending"),
        UserCard(id="c1", user_id=alice.id, character_id="x", set_id="s", rarity_id="common",
                 quality_id="fair", specialty_id="normal", jewelry_id="none", power=5),
        UserResource(user_id=alice.id, resource_id="dust", amount=777),
        UserResource(user_id=alice.id, resource_id="frag_legendary", amount=9),
        FavoriteCategory(user_id=alice.id, name="Top", color="#fff"),
        UserActivity(user_id=alice.id, machine_failures={"rarity_chances": 3}, converter_uses=2),
        UserBoosterInventory(user_id=alice.id, booster_id="b", quantity=4),
        RefreshToken(user_id=alice.id, token_hash="h", expires_at=alice.created_at),
    ])
    await session.commit()
    await guilds.create(session, alice, "Guilde", "GLD", "🛡️", "#fff", "open")

    alice_id = alice.id
    result = await season_reset.reset_all_accounts(session)
    assert result["users"] == 3

    session.expire_all()
    alice = await session.get(User, alice_id)
    assert (alice.coins, alice.packs_opened, alice.gift_policy) == (300, 0, "everyone")
    assert (alice.claimed_level, alice.max_level, alice.best_global_rank) == (0, 1, None)
    assert await session.get(UserResource, (alice_id, "frag_legendary")) is None
    for model in (FavoriteCategory, UserActivity, UserBoosterInventory):
        assert (await session.execute(model.__table__.select())).all() == []
    assert await session.get(UserCard, "c1") is None
    assert (await session.get(UserResource, (alice_id, "dust"))).amount == 50
    friendships = (await session.execute(FriendRequest.__table__.select())).all()
    assert [f.status for f in friendships] == ["accepted"]
    assert (await session.execute(RefreshToken.__table__.select())).all() == []
    assert await guilds.membership(session, alice_id) is None


async def test_closed_game_refuses_players_but_not_admin(session, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_KEY", "admin-test")
    game_status.invalidate()
    await game_status.ensure_open(session)  # ouvert par défaut

    session.add(GameConfig(id=1, game_closed=True, closed_message="Merci !"))
    await session.commit()
    game_status.invalidate()
    with pytest.raises(HTTPException) as exc:
        await game_status.ensure_open(session)
    assert exc.value.status_code == 503 and exc.value.detail["message"] == "Merci !"
    await game_status.ensure_open(session, "admin-test")

    game_status.invalidate()
