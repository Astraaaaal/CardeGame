"""
Cadeau « au choix » : le joueur reçoit une seule des bordures proposées,
celle qu'il désigne à la récupération.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models.message import Message
from app.models.premium import UserCosmetic
from app.services import beta_gift, message_rewards, messages
from app.services.beta_gift import BETA_FRAME_IDS
from tests.conftest import make_user


async def _prepare(session):
    await beta_gift.seed_frames(session)
    await session.commit()
    user = await make_user(session)
    message = Message(
        sender_type="admin", recipient_user_id=user.id,
        subject="Bienvenue dans la bêta 2.0", body="Choisis ta bordure.",
        reward_items=[{"kind": "cosmetic_choice", "ids": list(BETA_FRAME_IDS)}],
    )
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return user, message


@pytest.mark.asyncio
async def test_les_cinq_bordures_sont_creees(session):
    await beta_gift.seed_frames(session)
    await beta_gift.seed_frames(session)  # idempotent
    await session.commit()
    from app.models.premium import Cosmetic
    rows = (await session.execute(select(Cosmetic))).scalars().all()
    assert {c.id for c in rows} == set(BETA_FRAME_IDS)
    assert all(c.kind == "avatar_frame" and c.animation == "none" for c in rows)


@pytest.mark.asyncio
async def test_validation_refuse_une_option_inconnue(session):
    with pytest.raises(HTTPException):
        await message_rewards.validate(session, [{"kind": "cosmetic_choice", "ids": ["inconnu", "autre"]}])


@pytest.mark.asyncio
async def test_validation_exige_au_moins_deux_options(session):
    await beta_gift.seed_frames(session)
    await session.commit()
    with pytest.raises(HTTPException):
        await message_rewards.validate(session, [{"kind": "cosmetic_choice", "ids": [BETA_FRAME_IDS[0]]}])


@pytest.mark.asyncio
async def test_recuperer_sans_choisir_est_refuse(session):
    _, message = await _prepare(session)
    with pytest.raises(HTTPException):
        await messages.claim(session, message)
    assert message.claimed_at is None


@pytest.mark.asyncio
async def test_un_choix_hors_liste_est_refuse(session):
    _, message = await _prepare(session)
    with pytest.raises(HTTPException):
        await messages.claim(session, message, {"0": "frame_qui_nexiste_pas"})


@pytest.mark.asyncio
async def test_le_joueur_ne_recoit_que_la_bordure_choisie(session):
    user, message = await _prepare(session)
    choisie = BETA_FRAME_IDS[2]

    claimed = await messages.claim(session, message, {"0": choisie})

    assert claimed.claimed_at is not None
    assert claimed.reward_items[0]["chosen_id"] == choisie
    possedes = (await session.execute(
        select(UserCosmetic.cosmetic_id).where(UserCosmetic.user_id == user.id)
    )).scalars().all()
    assert list(possedes) == [choisie]


@pytest.mark.asyncio
async def test_l_apercu_expose_les_options_et_le_choix(session):
    user, message = await _prepare(session)
    apercu = await message_rewards.describe(session, message.reward_items)
    assert [o["id"] for o in apercu[0]["options"]] == list(BETA_FRAME_IDS)
    assert apercu[0]["chosen_id"] is None

    await messages.claim(session, message, {"0": BETA_FRAME_IDS[0]})
    apercu = await message_rewards.describe(session, message.reward_items)
    assert apercu[0]["chosen_id"] == BETA_FRAME_IDS[0]


@pytest.mark.asyncio
async def test_on_ne_recupere_pas_deux_fois(session):
    _, message = await _prepare(session)
    await messages.claim(session, message, {"0": BETA_FRAME_IDS[1]})
    with pytest.raises(HTTPException):
        await messages.claim(session, message, {"0": BETA_FRAME_IDS[3]})
