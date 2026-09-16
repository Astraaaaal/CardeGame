"""
Demandes d'échange (app/services/trade_requests.py) : un joueur peut
proposer à plusieurs joueurs à la fois, la première acceptation ouvre la
session et annule les autres propositions des deux participants.
"""

import pytest
from fastapi import HTTPException
from sqlmodel import select

from app.models.social import TradeRequest
from app.services import trade_requests as tr
from tests.conftest import make_user


async def _open_to_everyone(session, *users):
    for u in users:
        u.trade_request_policy = "everyone"
        session.add(u)
    await session.commit()


async def _pending(session):
    return (await session.execute(select(TradeRequest).where(TradeRequest.status == "pending"))).scalars().all()


async def test_first_accept_starts_trade_and_cancels_other_proposals(session):
    alice, bob, carol, dave = [await make_user(session, n) for n in ("alice", "bob", "carol", "dave")]
    await _open_to_everyone(session, alice, bob, carol, dave)

    to_bob = await tr.create_trade_request(session, alice, bob)
    to_carol = await tr.create_trade_request(session, alice, carol)
    bob_to_dave = await tr.create_trade_request(session, bob, dave)
    dave_to_alice = await tr.create_trade_request(session, dave, alice)

    trade = await tr.accept_trade_request(session, to_bob.id, bob.id)
    assert {trade.user_a_id, trade.user_b_id} == {alice.id, bob.id}

    remaining = {r.id for r in await _pending(session)}
    assert to_carol.id not in remaining and bob_to_dave.id not in remaining
    # Une proposition REÇUE par un participant reste disponible pour plus tard.
    assert remaining == {dave_to_alice.id}

    # Carol ne peut plus accepter : la proposition d'Alice a disparu.
    with pytest.raises(HTTPException) as exc:
        await tr.accept_trade_request(session, to_carol.id, carol.id)
    assert exc.value.status_code == 404


async def test_cannot_propose_while_in_a_trade(session):
    alice, bob, carol = [await make_user(session, n) for n in ("alice", "bob", "carol")]
    await _open_to_everyone(session, alice, bob, carol)

    req = await tr.create_trade_request(session, alice, bob)
    await tr.accept_trade_request(session, req.id, bob.id)

    with pytest.raises(HTTPException) as exc:
        await tr.create_trade_request(session, alice, carol)
    assert exc.value.status_code == 409


async def test_pulse_reports_unseen_requests_then_active_trade(session):
    alice, bob = await make_user(session, "alice"), await make_user(session, "bob")
    await _open_to_everyone(session, alice, bob)

    req = await tr.create_trade_request(session, alice, bob)

    bob_pulse = await tr.build_pulse(session, bob)
    assert [r.id for r in bob_pulse.incoming_unseen] == [req.id]
    assert bob_pulse.incoming_ids == [req.id] and bob_pulse.active_session_id is None
    alice_pulse = await tr.build_pulse(session, alice)
    assert alice_pulse.outgoing_ids == [req.id] and alice_pulse.incoming_unseen == []

    req.seen = True
    session.add(req)
    await session.commit()
    assert (await tr.build_pulse(session, bob)).incoming_unseen == []

    trade = await tr.accept_trade_request(session, req.id, bob.id)
    alice_pulse = await tr.build_pulse(session, alice)
    assert alice_pulse.active_session_id == trade.id
    assert alice_pulse.active_other_display_name == "bob"
    assert alice_pulse.outgoing_ids == []
