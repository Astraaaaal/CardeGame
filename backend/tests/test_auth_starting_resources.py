"""
Inscription (app/services/auth_service.py) — le solde de départ (pièces et
ressources secondaires) vient de Resource.starting_amount, éditable depuis
l'admin, plutôt que d'un 500 codé en dur.
"""

from app.models.economy import Resource, UserResource
from app.services.auth_service import AuthService

auth_service = AuthService()


async def test_register_grants_configured_starting_amounts(session):
    session.add(Resource(id="coins", name="Pièces", starting_amount=300))
    session.add(Resource(id="dust", name="Poussière", starting_amount=50))
    session.add(Resource(id="gems", name="Gemmes", starting_amount=0))
    await session.commit()

    user = await auth_service.register(session, "newplayer", "password123", "newplayer@example.com")

    assert user.coins == 300

    dust_row = await session.get(UserResource, (user.id, "dust"))
    assert dust_row is not None
    assert dust_row.amount == 50

    gems_row = await session.get(UserResource, (user.id, "gems"))
    assert gems_row is None  # starting_amount=0 -> pas de ligne créée


async def test_register_falls_back_to_500_coins_without_resource_row(session):
    user = await auth_service.register(session, "newplayer2", "password123", "newplayer2@example.com")
    assert user.coins == 500
