"""
Durcir les tables : à quoi ressemblerait le jeu si les paliers rares le
devenaient vraiment ?

Pour chaque scénario, dit combien de cartes et combien de JOURS il faut pour
voir chaque palier, et ce que le durcissement fait aux nombres qu'on vient
d'assagir (rareté affichée, valeur d'échange).

    python tools/simuler_tables.py                 # tous les scénarios
    python tools/simuler_tables.py --cartes 150    # à un autre rythme d'ouverture
    python tools/simuler_tables.py --scenario doux

Les scénarios sont de simples multiplicateurs de poids, en bas du fichier :
les modifier ne demande rien d'autre que de relancer la commande. Rien n'est
écrit nulle part, c'est un outil de réflexion.
"""

import argparse
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.power import DEFAULT_CAP, POWER_WEIGHT, TIER_CAPS  # noqa: E402

REFERENCE_SET = 10
# Rythme d'ouverture observé : ~57 boosters par jour à 5 cartes, une fois les
# pièces des activités, des quêtes et de la route dépensées en boosters.
CARTES_PAR_JOUR = 285
# Valeur d'échange : (rareté / ancrage) ^ exposant, plafonnée.
ANCRAGE, EXPOSANT, PLAFOND = 2.5, 1.15, 3000

# Poids de la production, axe par axe.
TABLES = {
    "rareté": [("common", 95), ("rare", 3), ("epic", 1.5), ("legendary", 0.5)],
    "qualité": [
        ("destroyed", 7.5), ("unreadable", 12.5), ("unplayable", 15), ("damaged", 25),
        ("torn", 18), ("scratched", 8), ("faded", 6), ("worn", 4), ("fair", 2.2),
        ("preserved", 1.5), ("excellent", 0.15), ("graded", 0.09), ("mint", 0.05),
        ("authentic", 0.01),
    ],
    "spécialité": [("normal", 99.8), ("full_art", 0.11), ("ex", 0.08), ("shiny", 0.01)],
    "bijou": [("none", 98), ("silver", 1.3), ("gold", 0.5), ("diamond", 0.15), ("prismatic", 0.05)],
}
# Le palier « banal » de chaque axe, qui absorbe ce qu'on retire aux autres.
SOCLE = {"rareté": "common", "qualité": "damaged", "spécialité": "normal", "bijou": "none"}
AXE_VERS_CAP = {"rareté": "rarity", "qualité": "quality", "spécialité": "specialty", "bijou": "jewelry"}

# Les paliers qu'on regarde : les autres n'intéressent personne.
REMARQUABLES = {
    "rareté": ["rare", "epic", "legendary"],
    "qualité": ["preserved", "excellent", "graded", "mint", "authentic"],
    "spécialité": ["full_art", "ex", "shiny"],
    "bijou": ["silver", "gold", "diamond", "prismatic"],
}


def appliquer(scenario: dict) -> dict:
    """Applique les multiplicateurs, le palier banal absorbant la différence."""
    out = {}
    for axe, rows in TABLES.items():
        facteurs = scenario.get(axe, {})
        socle = SOCLE[axe]
        nouveaux = [(i, w * facteurs.get(i, 1.0)) for i, w in rows]
        retire = sum(w for i, w in rows if i != socle) - sum(w for i, w in nouveaux if i != socle)
        out[axe] = [(i, w + retire if i == socle else w) for i, w in nouveaux]
    return out


def parts(rows):
    total = sum(w for _, w in rows)
    return {i: w / total for i, w in rows}


def duree(probabilite: float, cartes_par_jour: int) -> str:
    if probabilite <= 0:
        return "jamais"
    cartes = 1 / probabilite
    jours = cartes / cartes_par_jour
    if jours < 1:
        return f"{cartes:>9,.0f} cartes   {jours * 24:>5.1f} h".replace(",", " ")
    if jours < 365:
        return f"{cartes:>9,.0f} cartes   {jours:>5.1f} j".replace(",", " ")
    return f"{cartes:>9,.0f} cartes   {jours / 365:>5.1f} ans".replace(",", " ")


def collection(tables: dict, n: int = 60_000):
    """Raretés affichées et valeurs d'échange d'un échantillon de cartes."""
    p_axes = {axe: parts(rows) for axe, rows in tables.items()}
    listes = {axe: (list(p.keys()), list(p.values())) for axe, p in p_axes.items()}
    random.seed(21)
    raretes, valeurs = [], []
    for _ in range(n):
        proba, ids = 1 / REFERENCE_SET, {}
        for axe, (cles, poids) in listes.items():
            choisi = random.choices(cles, weights=poids, k=1)[0]
            ids[AXE_VERS_CAP[axe]] = choisi
            proba *= p_axes[axe][choisi]
        cap = max(TIER_CAPS[a].get(t, DEFAULT_CAP) for a, t in ids.items())
        plage = min(max(1, round(1 / proba)), cap)
        puissance = random.randint(1, plage)
        survie = (plage - puissance + 1) / plage
        rarete = round(1 / (proba * survie ** POWER_WEIGHT))
        raretes.append(rarete)
        valeurs.append(min(PLAFOND, (max(rarete, 1) / ANCRAGE) ** EXPOSANT))
    return sorted(raretes), sorted(valeurs)


SCENARIOS = {
    "actuel": {},
    # Un cran : le haut de chaque échelle devient trois fois plus rare.
    "doux": {
        "rareté": {"rare": 1 / 2, "epic": 1 / 3, "legendary": 1 / 3},
        "qualité": {"excellent": 1 / 3, "graded": 1 / 3, "mint": 1 / 3, "authentic": 1 / 3},
        "spécialité": {"full_art": 1 / 3, "ex": 1 / 3, "shiny": 1 / 3},
        "bijou": {"silver": 1 / 2, "gold": 1 / 3, "diamond": 1 / 3, "prismatic": 1 / 3},
    },
    # Le haut devient un événement : une légendaire tous les deux jours, une
    # prismatique tous les deux mois, une shiny une ou deux fois par saison.
    "marqué": {
        "rareté": {"rare": 1 / 3, "epic": 1 / 6, "legendary": 1 / 10},
        "qualité": {"preserved": 1 / 2, "excellent": 1 / 5, "graded": 1 / 8,
                    "mint": 1 / 10, "authentic": 1 / 10},
        "spécialité": {"full_art": 1 / 5, "ex": 1 / 8, "shiny": 1 / 10},
        "bijou": {"silver": 1 / 3, "gold": 1 / 6, "diamond": 1 / 8, "prismatic": 1 / 10},
    },
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cartes", type=int, default=CARTES_PAR_JOUR,
                        help="cartes ouvertes par jour (défaut : le rythme observé)")
    parser.add_argument("--scenario", action="append", choices=list(SCENARIOS),
                        help="n'en montrer que certains")
    args = parser.parse_args()
    choisis = args.scenario or list(SCENARIOS)

    print(f"Rythme retenu : {args.cartes} cartes ouvertes par jour "
          f"({args.cartes / 5:.0f} boosters)\n")

    resumes = {}
    for nom in choisis:
        tables = appliquer(SCENARIOS[nom])
        print(f"{'=' * 68}\n  SCÉNARIO « {nom} »\n{'=' * 68}")
        for axe, paliers in REMARQUABLES.items():
            p = parts(tables[axe])
            print(f"  --- {axe} ---")
            for palier in paliers:
                print(f"    {palier:<12}{p[palier] * 100:>8.4f} %   une {duree(p[palier], args.cartes)}")
        raretes, valeurs = collection(tables)
        resumes[nom] = (raretes, valeurs)
        print()

    print(f"{'=' * 68}\n  CE QUE ÇA FAIT AUX NOMBRES DÉJÀ ASSAGIS\n{'=' * 68}")
    print(f"  {'scénario':<10}{'rareté médiane':>18}{'rareté 99e c.':>18}"
          f"{'valeur médiane':>17}{'valeur 99e c.':>16}")
    for nom in choisis:
        r, v = resumes[nom]
        i99 = int(0.99 * len(r))
        print(f"  {nom:<10}{r[len(r) // 2]:>18,}{r[i99]:>18,}"
              f"{v[len(v) // 2]:>17,.0f}{v[i99]:>16,.0f}".replace(",", " "))
    print("\n  Durcir une table rend les cartes plus rares À L'AFFICHAGE et donc plus")
    print("  chères à l'échange. La PUISSANCE, elle, ne bouge pas : les paliers")
    print("  concernés sont déjà à leur plafond, et un plafond ne se dépasse pas.")
    return 0


raise SystemExit(main())
