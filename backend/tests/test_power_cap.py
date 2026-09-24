"""
Puissance tirée avec de la chance : la plage peut s'élargir (plus de chances
d'atteindre le maximum), mais la puissance ne dépasse jamais le maximum de
base de la carte, et la probabilité enregistrée reste celle de base.
"""

from app.models.character import Character, CharacterSet
from app.models.reference import Jewelry, Quality, Rarity, Specialty
from app.services.card_generator import CardGeneratorService
from app.services.power import power_range, roll_drawn_power


async def _reference(session):
    session.add(Character(id="c", name="C", type="feu", image_url="c.png"))
    session.add(Character(id="d", name="D", type="eau", image_url="d.png"))
    session.add_all([
        CharacterSet(character_id="c", set_id="s1", weight=1),
        CharacterSet(character_id="d", set_id="s2", weight=9),
        Rarity(id="common", name="Commune", weight=90), Rarity(id="rare", name="Rare", weight=10),
        Quality(id="fair", name="Correcte", weight=1), Specialty(id="normal", name="Normale", weight=1),
        Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()


async def test_lucky_draw_never_exceeds_base_max(session):
    await _reference(session)
    generator = CardGeneratorService()
    for _ in range(40):
        [data] = await generator.generate_pack(
            session, ["s1", "s2"], cards_count=1, guaranteed_rare=False, rarity_weight_multiplier=5.0,
        )
        # Probabilité de base : le set de la carte seul, raretés non modifiées.
        expected = 0.9 if data["rarity_id"] == "common" else 0.1
        assert abs(data["drop_probability"] - expected) < 1e-9
        assert data["draw_probability"] != data["drop_probability"]
        # La plage de puissance se calcule sur `power_probability` (taille de set
        # normalisée), pas sur la rareté affichée.
        base_max = power_range(data["power_probability"], data["rarity_id"], "fair", "normal", "none")
        assert 1 <= roll_drawn_power(data) <= base_max


def test_wider_draw_range_is_capped_at_base_max():
    data = {"drop_probability": 0.01, "draw_probability": 0.0001,
            "rarity_id": "common", "quality_id": "fair", "specialty_id": "normal", "jewelry_id": "none"}
    powers = [roll_drawn_power(data) for _ in range(300)]
    assert max(powers) == 100  # plage élargie à 10 000, résultat ramené à 100
    assert powers.count(100) > 200  # ~99 % des tirages atteignent le maximum


async def test_guarantee_raises_to_the_floor_without_boosting_higher_tiers(session):
    session.add(Character(id="c", name="C", type="feu", image_url="c.png"))
    session.add_all([
        CharacterSet(character_id="c", set_id="s1", weight=1),
        Rarity(id="common", name="Commune", weight=90), Rarity(id="epic", name="Épique", weight=9.5),
        Rarity(id="legendary", name="Légendaire", weight=0.5),
        Quality(id="fair", name="Correcte", weight=1), Specialty(id="normal", name="Normale", weight=1),
        Jewelry(id="none", name="Aucun", weight=1),
    ])
    await session.commit()
    generator = CardGeneratorService()
    rarities = []
    for _ in range(3000):
        [card] = await generator.generate_pack(session, ["s1"], cards_count=1, guaranteed_rare=False,
                                               force_min_rarity_id="epic")
        rarities.append(card["rarity_id"])
        if card["rarity_id"] == "epic":
            # Épique « garantie » : compte comme presque certaine (commune + épique remontées).
            assert abs(card["drop_probability"] - 0.995) < 1e-9
        else:
            assert abs(card["drop_probability"] - 0.005) < 1e-9  # légendaire : sa vraie rareté
    assert "common" not in rarities
    assert rarities.count("legendary") / len(rarities) < 0.02  # ~0,5 %, pas ~5 %
