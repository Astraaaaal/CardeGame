"""
Portefeuille (app/services/wallet.py) — "coins" est routé vers User.coins,
toute autre ressource vers UserResource. On vérifie que les deux chemins
lisent/écrivent bien le même total, y compris avec un delta négatif.
"""

from app.services import wallet
from tests.conftest import make_user


async def test_coins_routes_to_user_field(session):
    user = await make_user(session)
    assert await wallet.get_balance(session, user, "coins") == 500

    new_balance = await wallet.apply_delta(session, user, "coins", -150)

    assert new_balance == 350
    assert user.coins == 350


async def test_other_resource_routes_to_user_resource_table(session):
    user = await make_user(session)
    assert await wallet.get_balance(session, user, "dust") == 0

    await wallet.apply_delta(session, user, "dust", 40)
    await session.commit()
    new_balance = await wallet.apply_delta(session, user, "dust", -10)

    assert new_balance == 30
    assert await wallet.get_balance(session, user, "dust") == 30
