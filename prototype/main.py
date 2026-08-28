"""
CardeGame — Point d'entrée principal.
Lance le jeu de collection de cartes.
"""

import sys
import os

# Ajouter le dossier racine au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.Game.game import Game


def main():
    """Lance le jeu."""
    print("=" * 40)
    print("CardeGame - v0.1.0 Alpha")
    print("=" * 40)

    game = Game()
    game.run()


if __name__ == "__main__":
    main()
