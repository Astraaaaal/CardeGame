"""
Puissance d'une carte — tirée aléatoirement au moment de l'obtention (pack,
reroll), à partir de sa probabilité de tirage réelle. Sert de base aux
classements (cf. app/api/leaderboard.py).

Formule : N = 1 / probabilité (arrondi), puis on tire un nombre aléatoire
entre 1 et N. N est plafonné pour éviter des puissances absurdes sur les
combos ultra-rares — la probabilité complète (personnage × rareté ×
qualité × spécialité × bijou) peut descendre à des valeurs infinitésimales
pour les meilleures combinaisons, ce qui donnerait des puissances de
plusieurs milliards sans plafond. Le plafond est plus haut (20000 au lieu
de 10000) pour les cartes qui ont déjà un signe de prestige propre
(légendaire, bijou prismatique/diamant, qualité excellente ou mieux, ou
une spécialité autre que normale) — indépendamment de si LEUR combinaison
exacte est statistiquement rare.
"""

import random
from typing import Optional

from app.services.tier_order import rank

BASE_CAP = 10000
PRESTIGE_CAP = 20000


def _is_prestige(rarity_id: str, quality_id: str, specialty_id: str, jewelry_id: str) -> bool:
    return (
        rarity_id == "legendary"
        or jewelry_id in ("prismatic", "diamond")
        or rank("quality", quality_id) >= rank("quality", "excellent")
        or specialty_id != "normal"
    )


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
    cap = PRESTIGE_CAP if _is_prestige(rarity_id, quality_id, specialty_id, jewelry_id) else BASE_CAP
    return min(max(1, round(1 / drop_probability)), cap)


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
