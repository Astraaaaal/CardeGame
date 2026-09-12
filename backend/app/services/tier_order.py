"""
Ordres de "meilleur -> pire" par axe (rareté / qualité / spécialité / jewelry).
Partagés entre le tri de la collection et le reroll "garanti égal ou mieux".
Un id absent de la table vaut 0 (pire que tout le reste).
"""

RARITY_ORDER = {"legendary": 4, "epic": 3, "rare": 2, "common": 1}
QUALITY_ORDER = {
    "authentic": 14, "mint": 13, "graded": 12, "excellent": 11,
    "preserved": 10, "fair": 9, "worn": 8, "faded": 7,
    "scratched": 6, "torn": 5, "damaged": 4,
    "unplayable": 3, "unreadable": 2, "destroyed": 1,
}
SPECIALTY_ORDER = {"shiny": 4, "ex": 3, "full_art": 2, "normal": 1}
JEWELRY_ORDER = {"prismatic": 5, "diamond": 4, "gold": 3, "silver": 2, "none": 1}

ORDER_MAPS = {
    "rarity": RARITY_ORDER,
    "quality": QUALITY_ORDER,
    "specialty": SPECIALTY_ORDER,
    "jewelry": JEWELRY_ORDER,
}


def rank(axis: str, item_id: str) -> int:
    return ORDER_MAPS[axis].get(item_id, 0)
