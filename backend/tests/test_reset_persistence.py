"""
Ce qui doit traverser une remise à zéro : les cosmétiques possédés et équipés
(souvent payés), et les distinctions permanentes. Ce qui ne doit pas : les
distinctions saisonnières.
"""

import pytest
from sqlmodel import select

from app.models.distinction import BETA_TESTER_ID, Distinction, UserDistinction
from app.models.premium import Cosmetic, UserCosmetic
from app.services import beta_gift, distinctions, premium, season_reset
from tests.conftest import make_user


@pytest.mark.asyncio
async def test_les_cosmetiques_survivent_a_la_remise_a_zero(session):
    await beta_gift.seed_frames(session)
    user = await make_user(session)
    await premium.grant_cosmetic(session, user.id, "frame_beta_prune")
    user.equipped_avatar_frame_id = "frame_beta_prune"
    session.add(user)
    await session.commit()

    await season_reset.reset_all_accounts(session)

    possedes = (await session.execute(
        select(UserCosmetic.cosmetic_id).where(UserCosmetic.user_id == user.id)
    )).scalars().all()
    assert list(possedes) == ["frame_beta_prune"]

    await session.refresh(user)
    assert user.equipped_avatar_frame_id == "frame_beta_prune", "la décoration équipée reste en place"


@pytest.mark.asyncio
async def test_une_distinction_permanente_reste(session):
    await distinctions.seed_built_in(session)
    user = await make_user(session)
    await distinctions.grant(session, user.id, BETA_TESTER_ID)
    await session.commit()

    await season_reset.reset_all_accounts(session)

    assert [d.id for d in await distinctions.for_user(session, user.id)] == [BETA_TESTER_ID]


@pytest.mark.asyncio
async def test_une_distinction_saisonniere_repart(session):
    user = await make_user(session)
    session.add(Distinction(
        id="champion_septembre", name="Champion de septembre",
        keeps_on_reset=False,
    ))
    await session.commit()
    await distinctions.grant(session, user.id, "champion_septembre")
    await session.commit()

    await season_reset.reset_all_accounts(session)

    assert await distinctions.for_user(session, user.id) == []
    # La définition, elle, n'est pas supprimée : seul le port l'est.
    assert await session.get(Distinction, "champion_septembre") is not None


@pytest.mark.asyncio
async def test_les_deux_sortes_cohabitent(session):
    await distinctions.seed_built_in(session)
    user = await make_user(session)
    session.add(Distinction(id="saison_1", name="Saison 1", keeps_on_reset=False))
    await session.commit()
    await distinctions.grant(session, user.id, BETA_TESTER_ID)
    await distinctions.grant(session, user.id, "saison_1")
    await session.commit()

    await season_reset.reset_all_accounts(session)

    restantes = {d.id for d in await distinctions.for_user(session, user.id)}
    assert restantes == {BETA_TESTER_ID}


@pytest.mark.asyncio
async def test_le_tag_vaut_permanent_par_defaut(session):
    """Oublier le tag ne doit jamais faire disparaître un badge."""
    session.add(Distinction(id="sans_tag", name="Sans tag"))
    await session.commit()
    assert (await session.get(Distinction, "sans_tag")).keeps_on_reset is True

    user = await make_user(session)
    await distinctions.grant(session, user.id, "sans_tag")
    await session.commit()
    await season_reset.reset_all_accounts(session)
    assert [d.id for d in await distinctions.for_user(session, user.id)] == ["sans_tag"]


@pytest.mark.asyncio
async def test_un_cosmetique_non_possede_ne_reapparait_pas(session):
    """Garde-fou : on ne conserve que ce qui était réellement acquis."""
    await beta_gift.seed_frames(session)
    user = await make_user(session)
    await session.commit()

    await season_reset.reset_all_accounts(session)

    possedes = (await session.execute(
        select(UserCosmetic.cosmetic_id).where(UserCosmetic.user_id == user.id)
    )).scalars().all()
    assert list(possedes) == []
    # Le catalogue, lui, est intact.
    assert len((await session.execute(select(Cosmetic))).scalars().all()) == 5
