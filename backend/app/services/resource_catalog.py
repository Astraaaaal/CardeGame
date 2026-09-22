"""
Ressources de recyclage : catalogue unique (noms, familles, valeurs) utilisé par
le seed, le recyclage, le convertisseur, la machine d'amélioration et la taxe.

Toute carte recyclée donne de la poussière ; selon ses paliers elle donne en
plus un fragment (rareté), un minerai (bijou), une matière de spécialité et une
poussière de qualité de plus en plus rare. Ces ressources servent à la machine
d'amélioration, aux offres de la boutique et aux cosmétiques.
"""

DUST_ID = "dust"

# (id, nom, description) — ordre d'affichage.
NEW_RESOURCES = [
    ("frag_rare", "Fragment rare", "Obtenu en recyclant une carte rare."),
    ("frag_epic", "Fragment épique", "Obtenu en recyclant une carte épique."),
    ("frag_legendary", "Fragment légendaire", "Obtenu en recyclant une carte légendaire."),
    ("silver_ore", "Argent brut", "Obtenu en recyclant une carte à bijou argent."),
    ("gold_nugget", "Pépite d'or", "Obtenue en recyclant une carte à bijou or."),
    ("rough_diamond", "Diamant brut", "Obtenu en recyclant une carte à bijou diamant."),
    ("prism_crystal", "Cristal prismatique", "Obtenu en recyclant une carte à bijou prismatique."),
    ("art_ink", "Encre d'art", "Obtenue en recyclant une carte full art."),
    ("ex_seal", "Sceau EX", "Obtenu en recyclant une carte EX."),
    ("glitter", "Paillettes", "Obtenues en recyclant une carte shiny."),
    ("dust_fine", "Poussière fine", "Obtenue en recyclant une carte délavée, usée ou correcte."),
    ("dust_lustrous", "Poussière lustrée", "Obtenue en recyclant une carte préservée ou excellente."),
    ("dust_pearly", "Poussière nacrée", "Obtenue en recyclant une carte gradée ou mint."),
    ("dust_star", "Poussière d'étoile", "Obtenue en recyclant une carte authentique."),
]

# Familles, du palier le plus bas au plus haut (conversion d'un palier à l'autre).
FAMILIES = [
    [DUST_ID, "dust_fine", "dust_lustrous", "dust_pearly", "dust_star"],
    ["frag_rare", "frag_epic", "frag_legendary"],
    ["silver_ore", "gold_nugget", "rough_diamond", "prism_crystal"],
    ["art_ink", "ex_seal", "glitter"],
]

# Valeur d'une unité, exprimée en poussière (revente, taxe d'échange).
DUST_VALUE = {
    "frag_rare": 20, "frag_epic": 100, "frag_legendary": 500,
    "silver_ore": 15, "gold_nugget": 50, "rough_diamond": 150, "prism_crystal": 500,
    "art_ink": 30, "ex_seal": 60, "glitter": 150,
    "dust_fine": 10, "dust_lustrous": 40, "dust_pearly": 120, "dust_star": 400,
}
COINS_PER_DUST = 5


def converter_pairs() -> list[dict]:
    """Paires du convertisseur : d'un palier à l'autre dans chaque famille (monter
    10 → 1, descendre 1 → 5) et revente / achat contre de la poussière (avec perte)."""
    pairs = []
    for family in FAMILIES:
        for low, high in zip(family, family[1:], strict=False):
            pairs.append({"from": low, "to": high, "give": 10, "get": 1, "max_in": 1000})
            pairs.append({"from": high, "to": low, "give": 1, "get": 5, "max_in": 100})
    for res_id, value in DUST_VALUE.items():
        if res_id in FAMILIES[0]:
            continue  # poussières : déjà reliées par leur famille
        pairs.append({"from": res_id, "to": DUST_ID, "give": 1, "get": max(1, value // 2), "max_in": 100})
        pairs.append({"from": DUST_ID, "to": res_id, "give": value * 2, "get": 1, "max_in": value * 2 * 20})
    return pairs


def coin_values() -> dict[str, int]:
    """Valeur en pièces d'une unité (taxe d'échange)."""
    return {res_id: value * COINS_PER_DUST for res_id, value in DUST_VALUE.items()}
