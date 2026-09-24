"""
Le facteur « quel personnage » dans la rareté affichée : la TAILLE du set est
neutralisée, le POIDS que l'admin donne à chaque personnage est conservé.

Sans la neutralisation, un set de cinquante personnages afficherait des cartes
cinq fois plus rares qu'un set de dix, pour exactement la même carte. Sans la
conservation du poids, un personnage volontairement rare dans son set
compterait comme les autres — le réglage n'aurait plus aucun effet.
"""

import pytest

from app.models.character import Character, CharacterSet
from app.models.reference import Jewelry, Quality, Rarity, Specialty
from app.services.card_generator import CardGeneratorService
from app.services.power import REFERENCE_SET_SIZE


async def _un_seul_axe(session):
    """Un seul palier par axe : la rareté affichée ne dépend plus que du personnage."""
    session.add_all([
        Rarity(id="common", name="Commune", weight=1), Quality(id="fair", name="Correcte", weight=1),
        Specialty(id="normal", name="Normale", weight=1), Jewelry(id="none", name="Aucun", weight=1),
    ])


async def _set(session, poids: dict[str, float]):
    await _un_seul_axe(session)
    for cid, w in poids.items():
        session.add(Character(id=cid, name=cid, type="feu"))
        session.add(CharacterSet(character_id=cid, set_id="s", weight=w))
    await session.commit()


async def _raretes(session, tirages=400) -> dict[str, float]:
    generator = CardGeneratorService()
    vues: dict[str, float] = {}
    for _ in range(tirages):
        [data] = await generator.generate_pack(session, ["s"], cards_count=1, guaranteed_rare=False)
        vues[data["character_id"]] = data["drop_probability"]
    return vues


@pytest.mark.parametrize("taille", [4, 10, 40])
async def test_la_taille_du_set_ne_change_pas_la_rarete_affichee(session, taille):
    await _set(session, {f"c{i}": 1 for i in range(taille)})
    raretes = await _raretes(session)
    assert raretes, "aucune carte tirée"
    # Poids égaux : chaque personnage vaut 1 / REFERENCE_SET_SIZE, quelle que
    # soit la taille réelle du set.
    for valeur in raretes.values():
        assert valeur == pytest.approx(1 / REFERENCE_SET_SIZE)


async def test_le_poids_du_personnage_compte_toujours(session):
    # « rare » pèse quatre fois moins que chacun de ses trois camarades.
    await _set(session, {"commun_a": 4, "commun_b": 4, "commun_c": 4, "rare": 1})
    raretes = await _raretes(session)
    assert "rare" in raretes, "le personnage rare n'est jamais sorti"

    # Moyenne des poids = 13 / 4. Le rare vaut 1 / 3,25 = 0,3077 fois la moyenne.
    assert raretes["rare"] == pytest.approx((1 / 3.25) / REFERENCE_SET_SIZE)
    assert raretes["commun_a"] == pytest.approx((4 / 3.25) / REFERENCE_SET_SIZE)
    # Et il est bien annoncé quatre fois plus rare que les autres.
    assert raretes["commun_a"] / raretes["rare"] == pytest.approx(4)
