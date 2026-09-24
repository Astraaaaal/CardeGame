"""
Audite la collection d'un joueur : ce qu'il a obtenu contre ce que les poids
du tirage prévoient. Répond à « ce joueur a-t-il eu de la chance, ou avons-nous
un problème ? » sans avoir à le deviner.

    python tools/auditer_joueur.py aureliee

Lecture seule. À lancer avec la DATABASE_URL de la base à examiner.
"""

import argparse
import asyncio
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import app.main  # noqa: F401,E402
from sqlmodel import select  # noqa: E402

from app.database import async_session  # noqa: E402
from app.models.card import UserCard  # noqa: E402
from app.models.character import Character  # noqa: E402
from app.models.reference import Jewelry, Quality, Rarity, Specialty  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.power import combined_rarity, power_range  # noqa: E402
from app.services.tier_order import rank  # noqa: E402

AXES = (("rarity", Rarity), ("quality", Quality), ("specialty", Specialty), ("jewelry", Jewelry))


def ligne_ecart(observe: int, attendu: float) -> str:
    """Écart en nombre d'écarts-types (loi binomiale). Au-delà de 3, c'est
    suspect ; au-delà de 5, ce n'est plus de la chance."""
    if attendu <= 0:
        return "  —  " if observe == 0 else " !!!! "
    sigma = math.sqrt(attendu)
    z = (observe - attendu) / sigma
    if abs(z) < 2:
        verdict = "normal"
    elif abs(z) < 3:
        verdict = "un peu haut" if z > 0 else "un peu bas"
    elif abs(z) < 5:
        verdict = "SUSPECT" if z > 0 else "très bas"
    else:
        verdict = "ANORMAL" if z > 0 else "ANORMAL (bas)"
    return f"{z:+5.1f} σ  {verdict}"


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pseudo")
    parser.add_argument("--rares", type=int, default=15, help="nombre de cartes rares à détailler")
    args = parser.parse_args()

    async with async_session() as session:
        user = (await session.execute(
            select(User).where(User.username == args.pseudo.strip().lower())
        )).scalars().first()
        if user is None:
            print(f"Aucun compte « {args.pseudo} ».")
            return 1

        cards = (await session.execute(
            select(UserCard).where(UserCard.user_id == user.id)
        )).scalars().all()
        if not cards:
            print(f"{user.username} n'a aucune carte.")
            return 0

        refs = {}
        for axe, model in AXES:
            rows = (await session.execute(select(model))).scalars().all()
            refs[axe] = rows
        noms = {c.id: c.name for c in (await session.execute(select(Character))).scalars().all()}

        n = len(cards)
        print(f"=== {user.username} — {n} cartes, {user.packs_opened} boosters ouverts ===")
        attendu_cartes = user.packs_opened * 5
        if attendu_cartes:
            print(f"    ({attendu_cartes} cartes attendues des boosters ; "
                  f"l'écart vient des expéditions, mini-jeux, cadeaux et recyclages)")

        for axe, _ in AXES:
            rows = sorted(refs[axe], key=lambda r: rank(axe, r.id))
            total_poids = sum(r.weight for r in rows) or 1.0
            print(f"\n--- {axe} ---")
            print(f"  {'palier':<14}{'obtenu':>8}{'attendu':>10}{'part':>9}   écart")
            champ = f"{axe}_id"
            for r in rows:
                observe = sum(1 for c in cards if getattr(c, champ) == r.id)
                p = r.weight / total_poids
                attendu = n * p
                if observe == 0 and attendu < 0.5:
                    continue  # palier trop rare pour dire quoi que ce soit
                print(f"  {r.id:<14}{observe:>8}{attendu:>10.1f}{p * 100:>8.2f}%   {ligne_ecart(observe, attendu)}")

        # Les cartes les plus rares réellement possédées.
        note = []
        for c in cards:
            rarete = combined_rarity(c.power, c.drop_probability, c.rarity_id,
                                     c.quality_id, c.specialty_id, c.jewelry_id)
            note.append((rarete or 0, c))
        note.sort(key=lambda t: t[0], reverse=True)
        print(f"\n--- Les {args.rares} cartes les plus rares de la collection ---")
        print(f"  {'personnage':<16}{'combinaison':<42}{'puissance':>13}   rareté globale")
        for rarete, c in note[:args.rares]:
            plage = power_range(c.power_probability or c.drop_probability, c.rarity_id,
                                c.quality_id, c.specialty_id, c.jewelry_id)
            combi = f"{c.rarity_id}·{c.quality_id}·{c.specialty_id}·{c.jewelry_id}"
            puissance = f"{c.power or 0} / {plage or 0}"
            globale = f"{rarete:,}".replace(",", " ")
            print(f"  {noms.get(c.character_id, c.character_id):<16}{combi:<42}"
                  f"{puissance:>13}   1 sur {globale}")

        # Une carte sur dix environ dépasse 90 % de son maximum : la puissance est
        # tirée uniformément, donc c'est attendu et non suspect. L'attendu se
        # calcule carte par carte : sur une petite plage, « 90 % ou plus »
        # couvre mécaniquement un peu plus d'un dixième des valeurs possibles.
        au_sommet = 0
        attendu_sommet = 0.0
        for c in cards:
            plage = power_range(c.power_probability or c.drop_probability, c.rarity_id,
                                c.quality_id, c.specialty_id, c.jewelry_id)
            if not c.power or not plage:
                continue
            seuil = math.ceil(0.9 * plage)
            attendu_sommet += (plage - seuil + 1) / plage
            if c.power >= seuil:
                au_sommet += 1
        print("")
        print("--- Puissance ---")
        print(f"  cartes à 90 % ou plus de leur maximum : {au_sommet} sur {n} "
              f"({au_sommet / n * 100:.1f} %)")
        print(f"  attendu : {attendu_sommet:.1f} ({attendu_sommet / n * 100:.1f} %) — "
              f"la puissance est tirée uniformément dans sa plage")
        print(f"  écart : {ligne_ecart(au_sommet, attendu_sommet)}")
        return 0


raise SystemExit(asyncio.run(main()))
