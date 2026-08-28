"""
Modèle Card — Représente une carte unique dans le jeu.
Chaque carte générée a un identifiant unique (UUID) et conserve
son apparence (qualité, spécialité, rareté) de manière permanente.
"""

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Card:
    """Une carte unique avec toutes ses propriétés."""

    # Identifiant unique de cette instance de carte
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Infos du personnage (depuis characters.json)
    character_id: str = ""
    name: str = ""
    description: str = ""
    character_type: str = ""
    gen: int = 1
    image_file: str = ""

    # Propriétés générées aléatoirement
    set_id: str = ""
    rarity_id: str = ""
    quality_id: str = ""
    specialty_id: str = ""
    jewelry_id: str = "none"

    # Noms affichables (remplis après génération)
    set_name: str = ""
    rarity_name: str = ""
    quality_name: str = ""
    specialty_name: str = ""
    jewelry_name: str = "Commune"

    # Couleur de la rareté pour l'affichage
    rarity_color: tuple = (200, 200, 200)

    # Couleur de la jewelry pour la bordure
    jewelry_color: tuple = (100, 100, 120)

    # Probabilité d'obtention de cette combinaison exacte (en %)
    drop_probability: float = 0.0

    # Chemin vers l'image finale rendue (cached)
    rendered_image_path: Optional[str] = None

    def to_dict(self) -> dict:
        """Sérialise la carte pour sauvegarde JSON."""
        return {
            "uid": self.uid,
            "character_id": self.character_id,
            "name": self.name,
            "description": self.description,
            "character_type": self.character_type,
            "gen": self.gen,
            "image_file": self.image_file,
            "set_id": self.set_id,
            "rarity_id": self.rarity_id,
            "quality_id": self.quality_id,
            "specialty_id": self.specialty_id,
            "jewelry_id": self.jewelry_id,
            "set_name": self.set_name,
            "rarity_name": self.rarity_name,
            "quality_name": self.quality_name,
            "specialty_name": self.specialty_name,
            "jewelry_name": self.jewelry_name,
            "rarity_color": list(self.rarity_color),
            "jewelry_color": list(self.jewelry_color),
            "drop_probability": self.drop_probability,
            "rendered_image_path": self.rendered_image_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Désérialise une carte depuis un dictionnaire JSON."""
        card = cls()
        card.uid = data.get("uid", str(uuid.uuid4()))
        card.character_id = data.get("character_id", "")
        card.name = data.get("name", "")
        card.description = data.get("description", "")
        card.character_type = data.get("character_type", "")
        card.gen = data.get("gen", 1)
        card.image_file = data.get("image_file", "")
        card.set_id = data.get("set_id", "")
        card.rarity_id = data.get("rarity_id", "")
        card.quality_id = data.get("quality_id", "")
        card.specialty_id = data.get("specialty_id", "")
        card.jewelry_id = data.get("jewelry_id", "none")
        card.set_name = data.get("set_name", "")
        card.rarity_name = data.get("rarity_name", "")
        card.quality_name = data.get("quality_name", "")
        card.specialty_name = data.get("specialty_name", "")
        card.jewelry_name = data.get("jewelry_name", "Commune")
        card.rarity_color = tuple(data.get("rarity_color", [200, 200, 200]))
        card.jewelry_color = tuple(data.get("jewelry_color", [100, 100, 120]))
        card.drop_probability = data.get("drop_probability", 0.0)
        card.rendered_image_path = data.get("rendered_image_path")
        return card

    def get_display_info(self) -> str:
        """Retourne un résumé textuel de la carte."""
        jewelry_str = f" {self.jewelry_name}" if self.jewelry_id != "none" else ""
        return (
            f"{self.name} [{self.rarity_name}] "
            f"({self.specialty_name}{jewelry_str}) - {self.quality_name}"
        )
