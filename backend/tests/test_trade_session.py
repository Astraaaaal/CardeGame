"""
Échange en direct (app/services/trade_session.py) — le coeur "argent" du
jeu : double ready + double confirm exécute l'échange atomiquement, et
surtout, si le solde d'un joueur a changé entre temps (dépensé ailleurs
pendant la négociation), l'exécution doit retirer l'objet invalide et
repasser en négociation plutôt que de laisser un joueur payer plus qu'il
n'a.
"""

from app.services import trade_session as ts
from app.services.wallet import apply_delta
from tests.conftest import make_user


async def test_full_trade_swaps_coins_both_ways(session):
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")

    trade = await ts.create_session(session, alice.id, bob.id)
    await ts.add_resource_item(session, trade, alice.id, "coins", 100)
    await ts.add_resource_item(session, trade, bob.id, "coins", 50)

    await ts.set_ready(session, trade, alice.id, True)
    await ts.set_ready(session, trade, bob.id, True)

    messages = await ts.confirm(session, trade, alice.id)
    assert messages == []
    messages = await ts.confirm(session, trade, bob.id)
    assert messages == []

    await session.refresh(trade)
    assert trade.status == ts.STATUS_COMPLETED
    # Taxe de 25 % (niveau maximum dans les tests) sur ce que chacun reçoit.
    assert alice.coins == 500 - 100 + 50 - 13
    assert bob.coins == 500 - 50 + 100 - 25


async def test_execute_rolls_back_when_balance_became_insufficient(session):
    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")

    trade = await ts.create_session(session, alice.id, bob.id)
    await ts.add_resource_item(session, trade, alice.id, "coins", 400)

    await ts.set_ready(session, trade, alice.id, True)
    await ts.set_ready(session, trade, bob.id, True)

    # Alice dépense ses pièces ailleurs pendant la négociation, avant la
    # double confirmation finale — son offre n'est plus honorable.
    await apply_delta(session, alice, "coins", -300)
    await session.commit()

    await ts.confirm(session, trade, alice.id)
    messages = await ts.confirm(session, trade, bob.id)

    assert len(messages) == 1
    assert "insuffisant" in messages[0]

    await session.refresh(trade)
    assert trade.status == ts.STATUS_NEGOTIATING
    assert trade.ready_a is False and trade.ready_b is False
    assert alice.coins == 200  # inchangé par le trade, la seule dépense reste la sienne
    assert bob.coins == 500


async def test_trade_expires_when_a_player_is_gone_for_five_minutes(session):
    from datetime import datetime, timedelta

    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    trade = await ts.create_session(session, alice.id, bob.id)
    now = datetime.utcnow()
    alice.last_seen = now
    bob.last_seen = now - timedelta(minutes=2)
    session.add_all([alice, bob])
    await session.commit()
    assert await ts.get_active_session_for(session, alice.id) is not None

    trade.created_at = now - timedelta(minutes=10)
    bob.last_seen = now - timedelta(minutes=6)
    session.add_all([trade, bob])
    await session.commit()
    assert await ts.get_active_session_for(session, alice.id) is None
    await session.refresh(trade)
    assert trade.status == ts.STATUS_EXPIRED


async def test_trade_swaps_boosters_with_bonus_and_rerolls(session):
    from app.models.booster import Booster
    from app.services import booster_inventory, reroll_inventory

    alice = await make_user(session, "alice")
    bob = await make_user(session, "bob")
    session.add(Booster(id="booster_T", name="Booster test", set_id="s", price=1, resource_id="coins"))
    await booster_inventory.grant_bonus(session, alice.id, "booster_T", "epic", 2.0, "Offre épique", 4)
    rules = {"reroll_rarity": True, "reroll_quality": False, "reroll_specialty": False,
             "reroll_jewelry": False, "reroll_power": False, "reroll_mode": "guaranteed_min"}
    await reroll_inventory.grant_rules(session, bob.id, None, "Reroll rareté", rules, 3)
    await session.commit()
    [alice_booster] = await booster_inventory.list_owned(session, alice.id)
    [bob_token] = await reroll_inventory.list_owned(session, bob.id)

    trade = await ts.create_session(session, alice.id, bob.id)
    await ts.add_booster_item(session, trade, alice.id, "booster_T", alice_booster["bonus_id"], 3)
    await ts.add_reroll_item(session, trade, bob.id, bob_token["id"], 2)

    out = await ts.build_out(session, trade, alice.id)
    assert [(i.item_type, i.amount, i.label) for i in out.my_items] == [("booster", 3, "Offre épique")]
    assert [(i.item_type, i.amount) for i in out.other_items] == [("reroll", 2)]

    await ts.set_ready(session, trade, alice.id, True)
    await ts.set_ready(session, trade, bob.id, True)
    assert await ts.confirm(session, trade, alice.id) == []
    assert await ts.confirm(session, trade, bob.id) == []

    await session.refresh(trade)
    assert trade.status == ts.STATUS_COMPLETED
    assert [(o["quantity"], o["bonus_label"]) for o in await booster_inventory.list_owned(session, alice.id)] == [(1, "Offre épique")]
    assert [(o["quantity"], o["bonus_label"]) for o in await booster_inventory.list_owned(session, bob.id)] == [(3, "Offre épique")]
    assert [(t["quantity"], t["axes"]) for t in await reroll_inventory.list_owned(session, alice.id)] == [(2, ["rarity"])]
    assert [t["quantity"] for t in await reroll_inventory.list_owned(session, bob.id)] == [1]
