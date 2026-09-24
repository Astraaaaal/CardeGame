"""
Puissance d'une carte — tirée aléatoirement au moment de l'obtention (pack,
reroll), à partir de sa probabilité de tirage réelle. Sert de base aux
classements (cf. app/api/leaderboard.py).

Formule : N = 1 / probabilité (arrondi), puis on tire un nombre aléatoire
entre 1 et N. N est plafonné selon la MEILLEURE caractéristique de la carte
(cf. TIER_CAPS) : une carte sans rien de mieux que commune / normale / sans
bijou / déchirée plafonne à 5 000, une shiny ou authentique jusqu'à 50 000.
Sans plafond, les combinaisons ultra-rares donneraient des milliards.
"""

import random
from typing import Optional


# Puissance maximale selon le palier atteint sur chaque caractéristique ;
# une carte prend le plafond de sa meilleure caractéristique.
TIER_CAPS = {
    "rarity": {"common": 500, "rare": 1_000, "epic": 1_500, "legendary": 2_000},
    "quality": {
        "destroyed": 500, "unreadable": 500, "unplayable": 500, "damaged": 500, "torn": 500,
        "scratched": 1_000, "faded": 1_000, "worn": 1_000, "fair": 1_500, "preserved": 1_500,
        "excellent": 2_500, "graded": 2_500, "mint": 3_500, "authentic": 5_000,
    },
    "specialty": {"normal": 500, "full_art": 2_500, "ex": 2_500, "shiny": 5_000},
    "jewelry": {"none": 500, "silver": 1_000, "gold": 1_500, "diamond": 2_500, "prismatic": 3_500},
}
DEFAULT_CAP = 500

# Taille de set servant de référence au calcul de la puissance. Sans elle, un
# set de 50 cartes rendrait chacune de ses cartes cinq fois plus rare — donc
# cinq fois plus puissante — alors que le joueur voit la même carte banale.
# La rareté AFFICHÉE garde la vraie taille du set : elle, elle est honnête.
REFERENCE_SET_SIZE = 10


def power_cap(rarity_id: str, quality_id: str, specialty_id: str, jewelry_id: str) -> int:
    tiers = {"rarity": rarity_id, "quality": quality_id, "specialty": specialty_id, "jewelry": jewelry_id}
    return max(TIER_CAPS[axis].get(tier, DEFAULT_CAP) for axis, tier in tiers.items())


def power_range(
    drop_probability: float,
    rarity_id: str,
    quality_id: str,
    specialty_id: str,
    jewelry_id: str,
) -> Optional[int]:
    """N : la plage [1, N] dans laquelle la puissance de CETTE carte est tirée."""
    if not drop_probability or drop_probability <= 0:
        return None
    return min(max(1, round(1 / drop_probability)), power_cap(rarity_id, quality_id, specialty_id, jewelry_id))


def roll_power(
    drop_probability: float,
    rarity_id: str,
    quality_id: str,
    specialty_id: str,
    jewelry_id: str,
) -> Optional[int]:
    """
    None si la carte n'a pas été obtenue par un tirage aléatoire (probabilité
    nulle — ex: achat direct d'une carte précise au shop).
    """
    n = power_range(drop_probability, rarity_id, quality_id, specialty_id, jewelry_id)
    if n is None:
        return None
    return random.randint(1, n)


def roll_drawn_power(card_data: dict, rolls: int = 1) -> Optional[int]:
    """
    Puissance d'une carte sortie du générateur. La chance du moment (présence,
    bonus de guilde, rareté minimum garantie, booster à plusieurs sets) change
    la probabilité réelle du tirage (`draw_probability`) et peut donc élargir
    la plage de tirage — mais le résultat est ramené au maximum de BASE de la
    carte (`drop_probability`, cf. CardGeneratorService) : la chance donne
    plus de chances d'atteindre ce maximum, jamais de le dépasser.
    """
    axes = (card_data["rarity_id"], card_data["quality_id"], card_data["specialty_id"], card_data["jewelry_id"])
    # `power_probability` ignore la taille du set (cf. REFERENCE_SET_SIZE) ;
    # on retombe sur `drop_probability` pour les cartes d'avant ce changement.
    base_prob = card_data.get("power_probability") or card_data["drop_probability"]
    base_max = power_range(base_prob, *axes)
    if base_max is None:
        return None
    draw_max = power_range(card_data.get("draw_probability") or base_prob, *axes) or base_max
    # Bonus « chances de puissance » : plusieurs tirages, le meilleur est gardé.
    best = max(random.randint(1, max(base_max, draw_max)) for _ in range(max(1, rolls)))
    return min(best, base_max)


def combined_rarity(
    power: Optional[int],
    drop_probability: float,
    rarity_id: str,
    quality_id: str,
    specialty_id: str,
    jewelry_id: str,
) -> Optional[int]:
    """
    Rareté globale d'UN exemplaire précis, exprimée en "1 sur X" (comme
    `drop_probability`) — combine DEUX probabilités indépendantes :
    - la rareté de la combinaison elle-même (`drop_probability`) ;
    - la probabilité d'avoir obtenu CETTE puissance ou mieux, sachant la
      plage [1, N] possible pour cette carte : (N - power + 1) / N.

    X = 1 / (drop_probability × cette deuxième probabilité).

    Une puissance au minimum (1) ne change rien : X = 1/drop_probability,
    identique à la rareté de base. Une puissance au maximum (N) élève X au
    carré, approximativement. Ça évite le piège d'un simple pourcentage
    normalisé (puissance/N) qui, en effaçant le poids de la rareté de base,
    ferait ressortir une commune tirée à son maximum comme "aussi rare"
    qu'une carte légendaire — alors qu'un tirage 1/1000 à 980 (X ≈ 47 600)
    doit rester plus rare qu'un tirage 1/1100 à 150 (X ≈ 1 270), et qu'une
    carte 1/5000 à 80% de son maximum doit rester plus rare qu'une commune
    1/10 tirée à 100% de son maximum.
    """
    if power is None or not drop_probability or drop_probability <= 0:
        return None
    n = power_range(drop_probability, rarity_id, quality_id, specialty_id, jewelry_id)
    if not n:
        return None
    power_survival = (n - power + 1) / n  # proba d'obtenir CETTE puissance ou mieux
    combined = drop_probability * power_survival
    if combined <= 0:
        return None
    return round(1 / combined)
