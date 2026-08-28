"""
Modèle Player — Représente le joueur et sa progression.
Chaque joueur a son propre dossier dans saves/<username>/.
"""

import json
import os
from .collection import Collection
from ..utils.constants import SAVES_DIR


class Player:
    """Joueur avec sa collection et ses ressources."""

    def __init__(self, name: str = "Joueur", save_dir: str = None):
        self.name = name
        self.coins: int = 500  # Monnaie de départ
        self.collection = Collection()
        self.packs_opened: int = 0
        self.total_cards_obtained: int = 0
        # Dossier de sauvegarde propre au joueur
        self._save_dir = save_dir or SAVES_DIR

    def can_afford(self, cost: int) -> bool:
        """Vérifie si le joueur peut payer."""
        return self.coins >= cost

    def spend(self, amount: int) -> bool:
        """Dépense des pièces. Retourne True si réussi."""
        if self.can_afford(amount):
            self.coins -= amount
            return True
        return False

    def earn(self, amount: int):
        """Gagne des pièces."""
        self.coins += amount

    def save(self):
        """Sauvegarde le profil joueur en JSON dans son dossier."""
        os.makedirs(self._save_dir, exist_ok=True)
        save_path = os.path.join(self._save_dir, "player_save.json")
        data = {
            "name": self.name,
            "coins": self.coins,
            "packs_opened": self.packs_opened,
            "total_cards_obtained": self.total_cards_obtained,
            "collection": self.collection.to_dict_list(),
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, save_dir: str = None) -> "Player":
        """Charge la sauvegarde depuis le dossier donné."""
        target_dir = save_dir or SAVES_DIR
        save_path = os.path.join(target_dir, "player_save.json")
        if not os.path.exists(save_path):
            return cls(save_dir=target_dir)
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            player = cls(
                name=data.get("name", "Joueur"),
                save_dir=target_dir
            )
            player.coins = data.get("coins", 500)
            player.packs_opened = data.get("packs_opened", 0)
            player.total_cards_obtained = data.get("total_cards_obtained", 0)
            player.collection = Collection.from_dict_list(
                data.get("collection", [])
            )
            return player
        except (json.JSONDecodeError, KeyError):
            return cls(save_dir=target_dir)
