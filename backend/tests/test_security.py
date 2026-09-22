"""
Passe sécurité : soldes jamais négatifs, recyclage et achat d'annonce qui ne
paient qu'une fois, noms réservés, code de récupération et jetons de session
à usage unique, plafond d'échecs de connexion, secrets de production.
"""

import pytest
from fastapi import HTTPException

from app.api.collection import recycle_cards
from app.api.players import buy_trade_listing
from app.config import DEV_JWT_SECRET, Settings
from app.core import ratelimit
from app.core.security import is_admin_key
from app.models.card import UserCard
from app.models.character import Character
from app.models.economy import Resource, UserResource
from app.models.reference import Jewelry, Quality, Rarity, Set, Specialty
from app.models.social import TradeListing
from app.schemas.economy import RecycleByIdsRequest
from app.services import names, wallet
from app.services.auth_service import AuthService
from tests.conftest import make_user


async def _reference(session):
    session.add_all([
        Resource(id="coins", name="Pièces", protected=True), Resource(id="dust", name="Poussière"),
        Set(id="s1", name="Set"), Character(id="c", name="C", type="feu", image_url="c.png"),
        Rarity(id="common", name="Commune", weight=90),
        Quality(id="fair", name="Correcte", weight=1),
        Specialty(id="normal", name="Normale", weight=1), Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()


async def _card(session, owner) -> UserCard:
    card = UserCard(user_id=owner.id, character_id="c", set_id="s1", rarity_id="common",
                    quality_id="fair", specialty_id="normal", jewelry_id="none", power=10, drop_probability=0.5)
    session.add(card)
    await session.commit()
    return card


# ── Portefeuille ──

async def test_withdrawal_above_balance_is_refused_and_changes_nothing(session):
    user = await make_user(session)
    with pytest.raises(HTTPException) as exc:
        await wallet.apply_delta(session, user, "coins", -501)
    assert exc.value.status_code == 400 and "il t'en manque 1" in exc.value.detail
    assert user.coins == 500

    await wallet.apply_delta(session, user, "dust", 30)  # ligne créée à la volée
    with pytest.raises(HTTPException):
        await wallet.apply_delta(session, user, "dust", -31)
    assert await wallet.get_balance(session, user, "dust") == 30


async def test_loaded_resource_row_stays_in_sync(session):
    user = await make_user(session)
    session.add(UserResource(user_id=user.id, resource_id="dust", amount=10))
    await session.commit()
    row = await session.get(UserResource, (user.id, "dust"))
    assert await wallet.apply_delta(session, user, "dust", 5) == 15
    assert row.amount == 15


# ── Recyclage et achat d'annonce ──

async def test_recycling_pays_only_for_cards_actually_removed(session):
    await _reference(session)
    user = await make_user(session)
    cards = [await _card(session, user) for _ in range(3)]

    result = await recycle_cards(RecycleByIdsRequest(card_ids=[c.id for c in cards]), user, session)
    # Puissance au maximum de la carte : fourchette 3 à 5 par carte (commune 1→5, correcte → poussière fine 1→5).
    assert 9 <= result.gained <= 15 and result.new_balance == result.gained and result.recycled_count == 3
    assert {g.resource_id for g in result.gains} == {"dust", "dust_fine"}

    with pytest.raises(HTTPException) as exc:  # déjà recyclées : rien de plus
        await recycle_cards(RecycleByIdsRequest(card_ids=[cards[0].id]), user, session)
    assert exc.value.status_code == 404
    assert await wallet.get_balance(session, user, "dust") == result.gained


async def test_a_listing_can_only_be_bought_once(session):
    await _reference(session)
    seller = await make_user(session, "seller")
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    card = await _card(session, seller)
    session.add(TradeListing(user_id=seller.id, slot=0, user_card_id=card.id, resource_id="coins", price=100, mode="buy_now"))
    await session.commit()

    await buy_trade_listing(seller.id, 0, alice, session)
    await session.refresh(card)
    assert card.user_id == alice.id

    with pytest.raises(HTTPException) as exc:
        await buy_trade_listing(seller.id, 0, bob, session)
    assert exc.value.status_code == 404
    await session.refresh(seller)
    assert seller.coins == 600 and bob.coins == 500


# ── Noms ──

@pytest.mark.parametrize("name", ["Administration", "Àdmin", "ad min", "Modérateur", "CardeGame", "Bo\u200bb", "   "])
def test_reserved_or_invisible_display_names_are_refused(name):
    with pytest.raises(HTTPException):
        names.clean_display_name(name)


def test_display_name_is_trimmed():
    assert names.clean_display_name("  Léa   la  Grande ") == "Léa la Grande"


async def test_reserved_username_cannot_register(session):
    with pytest.raises(HTTPException):
        await AuthService().register(session, "Admin", "secret1", "a@example.com")


# ── Sessions et connexion ──

async def test_refresh_token_is_single_use(session):
    auth = AuthService()
    await auth.register(session, "alice", "secret1", "alice@example.com")
    tokens = await auth.login(session, "alice", "secret1")
    assert (await auth.refresh_tokens(session, tokens["refresh_token"]))["access_token"]
    with pytest.raises(HTTPException) as exc:
        await auth.refresh_tokens(session, tokens["refresh_token"])
    assert exc.value.status_code == 401


async def test_login_failures_are_capped_per_account(session):
    auth = AuthService()
    await auth.register(session, "carol", "secret1", "carol@example.com")
    ratelimit.clear_login_failures("carol")
    for _ in range(ratelimit.LOGIN_MAX_FAILURES):
        with pytest.raises(HTTPException) as exc:
            await auth.login(session, "carol", "mauvais")
        assert exc.value.status_code == 401
    with pytest.raises(HTTPException) as exc:  # même le bon mot de passe attend
        await auth.login(session, "carol", "secret1")
    assert exc.value.status_code == 429
    ratelimit.clear_login_failures("carol")
    assert (await auth.login(session, "CAROL", "secret1"))["access_token"]


# ── Secrets ──

def test_production_refuses_default_or_short_jwt_secret():
    with pytest.raises(RuntimeError):
        Settings(ENVIRONMENT="production", JWT_SECRET=DEV_JWT_SECRET).check_production_secrets()
    with pytest.raises(RuntimeError):
        Settings(ENVIRONMENT="production", JWT_SECRET="court").check_production_secrets()
    Settings(ENVIRONMENT="production", JWT_SECRET="x" * 40).check_production_secrets()
    Settings(ENVIRONMENT="development", JWT_SECRET=DEV_JWT_SECRET).check_production_secrets()


def test_admin_key_check(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "ADMIN_KEY", "")
    assert not is_admin_key("")
    monkeypatch.setattr(settings, "ADMIN_KEY", "cle-admin")
    assert is_admin_key("cle-admin") and not is_admin_key("cle-admiN") and not is_admin_key("")
