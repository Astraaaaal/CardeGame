"""
Remet des réglages stockés à leur valeur par défaut du code.

`save_config` fige une copie COMPLÈTE des réglages en base : un changement de
valeur par défaut dans le code ne redescend donc jamais tout seul jusqu'au jeu.
Après une passe d'équilibrage, ce script rejoue les clés concernées — et elles
seules, pour ne pas écraser les réglages volontairement modifiés en admin.

    python tools/reappliquer_reglages.py presence progression.presence_max \
        unlocks.higher_lower unlocks.showcase
    python tools/reappliquer_reglages.py --appliquer presence ...

Sans --appliquer, affiche seulement ce qui changerait.
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import app.main  # noqa: F401,E402  (charge les modèles et la configuration)
from app.database import async_session  # noqa: E402
from app.models.game_config import GameConfig  # noqa: E402
from app.services.activities_config import DEFAULTS  # noqa: E402


def lire(source: dict, chemin: str):
    valeur = source
    for partie in chemin.split("."):
        if not isinstance(valeur, dict) or partie not in valeur:
            raise KeyError(chemin)
        valeur = valeur[partie]
    return valeur


def ecrire(cible: dict, chemin: str, valeur) -> None:
    parties = chemin.split(".")
    for partie in parties[:-1]:
        cible = cible.setdefault(partie, {})
    cible[parties[-1]] = valeur


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("chemins", nargs="+", help="clés à rejouer, ex. progression.presence_max")
    parser.add_argument("--appliquer", action="store_true", help="écrit en base (sinon simple aperçu)")
    args = parser.parse_args()

    async with async_session() as session:
        config = await session.get(GameConfig, 1)
        if config is None or not config.activities:
            print("Aucun réglage enregistré : les défauts du code s'appliquent déjà.")
            return 0

        stockes = dict(config.activities)
        changements = []
        for chemin in args.chemins:
            attendu = lire(DEFAULTS, chemin)
            try:
                actuel = lire(stockes, chemin)
            except KeyError:
                actuel = None
            if actuel != attendu:
                changements.append((chemin, actuel, attendu))
                ecrire(stockes, chemin, attendu)

        if not changements:
            print("Rien à faire : la base est déjà alignée sur le code.")
            return 0
        for chemin, actuel, attendu in changements:
            print(f"  {chemin} : {actuel}  ->  {attendu}")
        if not args.appliquer:
            print("\nAperçu seulement. Relancer avec --appliquer pour écrire.")
            return 0

        config.activities = stockes
        session.add(config)
        await session.commit()
        print(f"\n{len(changements)} réglage(s) remis à jour.")
        return 0


raise SystemExit(asyncio.run(main()))
