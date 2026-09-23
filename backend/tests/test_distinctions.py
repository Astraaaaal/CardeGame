"""
Distinctions accordées : attribution idempotente, survie à la remise à zéro
des comptes, et marquage automatique des acheteurs.
"""

from datetime import datetime

import pytest
from sqlmodel import select

from app.models.distinction import BETA_TESTER_ID, FOUNDER_ID, Distinction, UserDistinction
from app.models.premium import ORDER_PAID, PremiumOrder
from app.services import distinctions, season_reset
from tests.conftest import make_user


async def _seed(session):
    await distinctions.seed_built_in(session)
    await session.commit()


@pytest.mark.asyncio
async def test_seed_est_idempotent(session):
    await _seed(session)
    await _seed(session)
    rows = (await session.execute(select(Distinction))).scalars().all()
    assert {d.id for d in rows} == {BETA_TESTER_ID, FOUNDER_ID}


@pytest.mark.asyncio
async def test_seed_respecte_une_personnalisation(session):
    """Une distinction renommée depuis l'admin n'est pas réécrite au démarrage."""
    await _seed(session)
    row = await session.get(Distinction, BETA_TESTER_ID)
    row.name = "Pionnier"
    session.add(row)
    await session.commit()

    await _seed(session)
    assert (await session.get(Distinction, BETA_TESTER_ID)).name == "Pionnier"


@pytest.mark.asyncio
async def test_attribution_sans_doublon(session):
    await _seed(session)
    user = await make_user(session)

    assert await distinctions.grant(session, user.id, BETA_TESTER_ID) is True
    await session.commit()
    assert await distinctions.grant(session, user.id, BETA_TESTER_ID) is False
    await session.commit()

    held = (await session.execute(
        select(UserDistinction).where(UserDistinction.user_id == user.id)
    )).scalars().all()
    assert len(held) == 1


@pytest.mark.asyncio
async def test_attribution_en_masse_ignore_ceux_qui_l_ont(session):
    await _seed(session)
    a = await make_user(session, "a")
    b = await make_user(session, "b")
    await distinctions.grant(session, a.id, BETA_TESTER_ID)
    await session.commit()

    granted = await distinctions.grant_many(session, [a.id, b.id], BETA_TESTER_ID)
    await session.commit()
    assert granted == 1

    porteurs = await distinctions.for_user(session, b.id)
    assert [d.id for d in porteurs] == [BETA_TESTER_ID]


@pytest.mark.asyncio
async def test_distinction_inactive_masquee(session):
    await _seed(session)
    user = await make_user(session)
    await distinctions.grant(session, user.id, BETA_TESTER_ID)
    row = await session.get(Distinction, BETA_TESTER_ID)
    row.active = False
    session.add(row)
    await session.commit()

    assert await distinctions.for_user(session, user.id) == []


@pytest.mark.asyncio
async def test_les_distinctions_survivent_a_la_remise_a_zero(session):
    """Le cœur du sujet : le cadeau ne doit pas partir avec le reste."""
    await _seed(session)
    user = await make_user(session)
    await distinctions.grant(session, user.id, BETA_TESTER_ID)
    await session.commit()

    await season_reset.reset_all_accounts(session)

    porteurs = await distinctions.for_user(session, user.id)
    assert [d.id for d in porteurs] == [BETA_TESTER_ID]


@pytest.mark.asyncio
async def test_la_remise_a_zero_grave_les_fondateurs(session):
    """Les commandes sont détachées des comptes par le reset : sans ce
    marquage, plus personne ne saurait qui avait soutenu le jeu."""
    await _seed(session)
    acheteur = await make_user(session, "acheteur")
    curieux = await make_user(session, "curieux")
    session.add(PremiumOrder(
        user_id=acheteur.id, product_id="pack", product_name="Pack",
        amount_cents=500, status=ORDER_PAID, paid_at=datetime.utcnow(),
    ))
    await session.commit()

    result = await season_reset.reset_all_accounts(session)
    assert result["founders_granted"] == 1

    assert [d.id for d in await distinctions.for_user(session, acheteur.id)] == [FOUNDER_ID]
    assert await distinctions.for_user(session, curieux.id) == []
