"""
Puissance d'une carte — tirée aléatoirement au moment de l'obtention (pack,
reroll), à partir de sa probabilité de tirage réelle. Sert de base aux
classements (cf. app/api/leaderboard.py).

Formule : N = 1 / probabilité (arrondi), puis on tire un nombre aléatoire
entre 1 et N. N est plafonné pour éviter des puissances absurdes sur les
combos ultra-rares — la probabilité complète (personnage × rareté ×
qualité × spécialité × bijou) peut descendre à des valeurs infinitésimales
pour les meilleures combinaisons, ce qui donnerait des puissances de
plusieurs milliards sans plafond. Le plafond est plus haut (2000 au lieu
de 1000) pour les cartes qui ont déjà un signe de prestige propre
(légendaire, bijou prismatique/diamant, qualité excellente ou mieux, ou
une spécialité autre que normale) — indépendamment de si LEUR combinaison
exacte est statistiquement rare.
"""

import random
from typing import Optional

from app.services.tier_order import rank

BASE_CAP = 1000
PRESTIGE_CAP = 2000


def _is_prestige(rarity_id: str, quality_id: str, specialty_id: str, jewelry_id: str) -> bool:
    return (
        rarity_id == "legendary"
        or jewelry_id in ("prismatic", "diamond")
        or rank("quality", quality_id) >= rank("quality", "excellent")
        or specialty_id != "normal"
    )


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
    if not drop_probability or drop_probability <= 0:
        return None
    cap = PRESTIGE_CAP if _is_prestige(rarity_id, quality_id, specialty_id, jewelry_id) else BASE_CAP
    n = min(max(1, round(1 / drop_probability)), cap)
    return random.randint(1, n)
