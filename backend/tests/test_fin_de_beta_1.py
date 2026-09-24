"""
La clôture de la première bêta, dans l'ordre où elle sera jouée en production :
remise à zéro, puis badge « Bêta testeur », puis message de remerciement avec
la bordure au choix.

L'ordre compte. Le badge est posé APRÈS la remise à zéro (avant, il serait
effacé si quelqu'un le marquait saisonnier), et le message part en dernier :
c'est lui que le joueur voit en se connectant, et la bordure qu'il choisit
doit atterrir sur un compte déjà remis à neuf.
"""

import pytest
from sqlmodel import select

from app.models.card import UserCard
from app.models.distinction import BETA_TESTER_ID, UserDistinction
from app.models.message import Message
from app.models.premium import ORDER_PAID, PremiumOrder, UserCosmetic
from app.services import beta_gift, distinctions, messages, premium, season_reset
from app.services.beta_gift import BETA_FRAME_IDS
from tests.conftest import make_user


def _carte(user_id, cid):
    return UserCard(id=cid, user_id=user_id, character_id="c", set_id="s", rarity_id="common",
                    quality_id="fair", specialty_id="normal", jewelry_id="none",
                    drop_probability=0.05, power=42)


@pytest.mark.asyncio
async def test_la_cloture_de_la_beta_1_de_bout_en_bout(session):
    await beta_gift.seed_frames(session)
    await distinctions.seed_built_in(session)
    joueur = await make_user(session, "ancien")
    nouveau = await make_user(session, "arrivant")

    # Un vétéran qui a joué, acheté, et équipé ce qu'il a acheté.
    session.add_all([_carte(joueur.id, "a"), _carte(joueur.id, "b")])
    await premium.grant_cosmetic(session, joueur.id, "frame_beta_prune")
    joueur.equipped_avatar_frame_id = "frame_beta_prune"
    joueur.coins = 12_345
    session.add_all([joueur, PremiumOrder(
        user_id=joueur.id, product_id="pack_eclats", product_name="Pack d'Éclats",
        status=ORDER_PAID, amount_cents=499, currency="eur",
    )])
    await session.commit()

    # 1. Remise à zéro.
    rapport = await season_reset.reset_all_accounts(session)
    assert rapport["cards_removed"] == 2
    assert (await session.execute(select(UserCard))).scalars().all() == []

    await session.refresh(joueur)
    assert joueur.coins != 12_345  # reparti du solde de départ
    assert joueur.max_level == 1
    # Ce qui a été payé reste : la bordure, son port, et la trace de l'achat.
    assert (await session.execute(select(UserCosmetic.cosmetic_id).where(
        UserCosmetic.user_id == joueur.id))).scalars().all() == ["frame_beta_prune"]
    assert joueur.equipped_avatar_frame_id == "frame_beta_prune"
    assert (await session.execute(select(PremiumOrder.product_id).where(
        PremiumOrder.user_id == joueur.id))).scalars().all() == ["pack_eclats"]

    # 2. Le badge, à tout le monde.
    ids = (await session.execute(select(type(joueur).id))).scalars().all()
    poses = await distinctions.grant_many(session, list(ids), BETA_TESTER_ID, reason="première bêta")
    await session.commit()
    assert poses == 2
    assert set((await session.execute(select(UserDistinction.user_id))).scalars().all()) == {joueur.id, nouveau.id}

    # 3. Le message, avec les cinq bordures au choix.
    envoyes = await messages.send_admin_broadcast(
        session, None, "Merci d'avoir joué à la première bêta",
        "Le jeu repart de zéro, mais pas toi.", None, None,
        [{"kind": "cosmetic_choice", "ids": list(BETA_FRAME_IDS)}],
    )
    assert envoyes == 2

    message = (await session.execute(select(Message).where(
        Message.recipient_user_id == joueur.id))).scalars().one()
    sortie = await messages.build_out(session, message)
    assert sortie.has_reward
    [recompense] = sortie.reward_items
    assert [o.id for o in recompense.options] == list(BETA_FRAME_IDS)

    # Le vétéran choisit une bordure qu'il n'avait pas : il en a deux au final.
    await messages.claim(session, message, choices={"0": "frame_beta_ambre"})
    possedes = (await session.execute(select(UserCosmetic.cosmetic_id).where(
        UserCosmetic.user_id == joueur.id))).scalars().all()
    assert sorted(possedes) == ["frame_beta_ambre", "frame_beta_prune"]
