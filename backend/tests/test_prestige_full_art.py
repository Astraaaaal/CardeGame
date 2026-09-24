"""
Full art réservé aux personnages cochés, niveaux de prestige après la route,
plafonds de puissance selon la meilleure caractéristique.
"""

from app.models.character import Character, CharacterSet
from app.models.level import LevelTier
from app.models.reference import Jewelry, Quality, Rarity, Specialty
from app.services import levels
from app.services.card_generator import CardGeneratorService
from app.services.power import REFERENCE_SET_SIZE, power_cap
from app.services.wallet import get_balance
from tests.conftest import make_user


async def _reference(session, full_art: bool):
    session.add(Character(id="c", name="C", type="feu", image_url="c.png",
                          full_art=full_art, full_art_image_url="c-full.png" if full_art else ""))
    session.add_all([
        CharacterSet(character_id="c", set_id="s1", weight=1),
        Rarity(id="common", name="Commune", weight=1), Quality(id="fair", name="Correcte", weight=1),
        Specialty(id="normal", name="Normale", weight=1), Specialty(id="full_art", name="Full art", weight=1),
        Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()


async def test_character_without_full_art_never_draws_it(session):
    await _reference(session, full_art=False)
    cards = await CardGeneratorService().generate_pack(session, ["s1"], cards_count=30, guaranteed_rare=False)
    assert {c["specialty_id"] for c in cards} == {"normal"}
    # « Normale » récupère la part du full art. La rareté affichée ramène en plus
    # le facteur personnage au set de référence (un seul personnage ici).
    attendu = 1.0 / REFERENCE_SET_SIZE
    assert all(abs(c["drop_probability"] - attendu) < 1e-9 for c in cards)


async def test_character_with_full_art_can_draw_it(session):
    await _reference(session, full_art=True)
    cards = await CardGeneratorService().generate_pack(session, ["s1"], cards_count=60, guaranteed_rare=False)
    assert "full_art" in {c["specialty_id"] for c in cards}


async def test_prestige_levels_follow_the_road(session):
    session.add_all([LevelTier(level=1, power_required=0),
                     LevelTier(level=2, power_required=1000, reward_resource_id="coins", reward_amount=100)])
    await session.commit()
    tiers = await levels.get_all_tiers(session)
    p1, p2 = tiers[2], tiers[3]
    assert (p1.level, p1.prestige, p1.power_required, p1.reward_amount) == (3, 1, 1250, 110)
    assert (p2.power_required, p2.reward_amount, p2.bonus_resource_id) == (1563, 120, "frag_legendary")

    user = await make_user(session)
    await levels.claim_level_rewards(session, user)  # puissance 0 : rien à récupérer au-delà du niveau 1
    assert await get_balance(session, user, "frag_legendary") == 0


def test_power_cap_is_the_best_tier():
    assert power_cap("common", "torn", "normal", "none") == 500
    assert power_cap("rare", "torn", "normal", "none") == 1_000
    assert power_cap("common", "fair", "normal", "gold") == 1_500
    assert power_cap("legendary", "torn", "full_art", "none") == 2_500
    assert power_cap("common", "mint", "normal", "none") == 3_500
    assert power_cap("epic", "authentic", "normal", "none") == 5_000
