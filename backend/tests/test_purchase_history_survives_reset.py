"""
L'historique des achats en euros survit à une remise à zéro et reste attaché
à son compte — c'est la preuve de ce qu'un joueur a payé. Seules les limites
« une fois par compte » se rouvrent.
"""

from datetime import datetime, timedelta

import pytest
from sqlmodel import select

from app.models.game_config import GameConfig
from app.models.premium import ORDER_PAID, PremiumOrder
from app.services import purchase_limits, season_reset
from tests.conftest import make_user


async def _acheteur(session, paid_at=None):
    user = await make_user(session, "acheteur")
    session.add(PremiumOrder(
        user_id=user.id, product_id="pack_depart", product_name="Pack de départ",
        amount_cents=990, status=ORDER_PAID, paid_at=paid_at or datetime.utcnow(),
    ))
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_la_commande_reste_attachee_au_compte(session):
    user = await _acheteur(session)

    await season_reset.reset_all_accounts(session)

    commandes = (await session.execute(
        select(PremiumOrder).where(PremiumOrder.user_id == user.id)
    )).scalars().all()
    assert len(commandes) == 1, "l'achat doit rester lié à son acheteur"
    assert commandes[0].amount_cents == 990
    assert commandes[0].status == ORDER_PAID


@pytest.mark.asyncio
async def test_la_remise_a_zero_horodate(session):
    await _acheteur(session)
    avant = datetime.utcnow()

    await season_reset.reset_all_accounts(session)

    config = await session.get(GameConfig, 1)
    assert config is not None and config.last_reset_at is not None
    assert config.last_reset_at >= avant - timedelta(seconds=5)


@pytest.mark.asyncio
async def test_une_offre_a_usage_unique_se_rouvre(session):
    """Le décompte repart, l'historique reste : les deux à la fois."""
    await _acheteur(session, paid_at=datetime.utcnow() - timedelta(days=2))

    await season_reset.reset_all_accounts(session)

    start = await purchase_limits.account_start(session)
    assert start is not None
    comptees = (await session.execute(
        select(PremiumOrder).where(
            PremiumOrder.status == ORDER_PAID, PremiumOrder.paid_at >= start,
        )
    )).scalars().all()
    assert comptees == [], "un achat d'avant la remise à zéro ne bloque plus l'offre"


@pytest.mark.asyncio
async def test_sans_remise_a_zero_tout_l_historique_compte(session):
    await _acheteur(session)
    assert await purchase_limits.account_start(session) is None
