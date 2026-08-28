"""
CardGenerator — Génère des cartes aléatoires pour les packs.
Gère les probabilités de rareté, qualité et spécialité.
"""

import random
from typing import List
from ..models.card import Card
from .data_manager import DataManager


class CardGenerator:
    """Génère des cartes avec tirage aléatoire pondéré."""

    def __init__(self, data_manager: DataManager):
        self.data = data_manager

    def generate_pack(self, booster_id: str) -> List[Card]:
        """Génère un pack complet de cartes pour un booster donné."""
        booster = self.data.get_booster(booster_id)
        if not booster:
            print(f"[CardGenerator] Booster '{booster_id}' introuvable!")
            return []

        set_id = booster["set"]
        cards_count = booster.get("cards_count", 5)
        guaranteed_rare = booster.get("guaranteed_rare", False)

        # Récupérer les personnages disponibles dans ce set
        available_characters = self.data.get_characters_for_set(set_id)
        if not available_characters:
            print(f"[CardGenerator] Aucun personnage dans le set '{set_id}'!")
            return []

        cards = []
        for i in range(cards_count):
            # Si guaranteed_rare et dernière carte, forcer rare minimum
            force_rare = (guaranteed_rare and i == cards_count - 1)
            card = self._generate_single_card(
                available_characters, set_id, force_rare
            )
            cards.append(card)

        return cards

    def _generate_single_card(self, characters: List[dict],
                               set_id: str,
                               force_rare: bool = False) -> Card:
        """Génère une seule carte aléatoire."""
        # 1. Choisir un personnage (pondéré par weight_per_set si dispo)
        char_weights = []
        for c in characters:
            wps = c.get("weight_per_set", {})
            char_weights.append(wps.get(set_id, 1))
        character = random.choices(characters, weights=char_weights, k=1)[0]

        # 2. Tirer la rareté (pondérée)
        rarity = self._weighted_random(
            self.data.rarities,
            exclude_ids=["common"] if force_rare else []
        )

        # 3. Tirer la qualité (pondérée)
        quality = self._weighted_random(self.data.qualities)

        # 4. Tirer la spécialité (pondérée)
        specialty = self._weighted_random(self.data.specialties)

        # 5. Tirer la jewelry (pondérée)
        jewelry = self._weighted_random(self.data.jewelries)

        # 6. Récupérer les infos du set
        set_info = self.data.get_set(set_id)

        # 7. Calculer la probabilité d'obtention
        drop_prob = self._calculate_probability(
            characters, character, set_id,
            rarity, quality, specialty, jewelry, force_rare
        )

        # 8. Construire la carte
        card = Card(
            character_id=character["id"],
            name=character["name"],
            description=character.get("description", ""),
            character_type=character.get("type", ""),
            gen=character.get("gen", 1),
            image_file=character.get("image", ""),
            set_id=set_id,
            set_name=set_info["name"] if set_info else set_id,
            rarity_id=rarity["id"],
            rarity_name=rarity["name"],
            rarity_color=tuple(rarity.get("color", [200, 200, 200])),
            quality_id=quality["id"],
            quality_name=quality["name"],
            specialty_id=specialty["id"],
            specialty_name=specialty["name"],
            jewelry_id=jewelry["id"],
            jewelry_name=jewelry["name"],
            jewelry_color=tuple(jewelry.get("color", [100, 100, 120])),
            drop_probability=drop_prob,
        )

        return card

    def _calculate_probability(self, characters: List[dict],
                                character: dict, set_id: str,
                                rarity: dict, quality: dict,
                                specialty: dict, jewelry: dict,
                                force_rare: bool = False) -> float:
        """Calcule la probabilité exacte d'obtenir cette combinaison."""
        # Proba du personnage (pondérée par weight_per_set)
        char_weights = []
        for c in characters:
            wps = c.get("weight_per_set", {})
            char_weights.append(wps.get(set_id, 1))
        char_total = sum(char_weights)
        my_weight = character.get("weight_per_set", {}).get(set_id, 1)
        char_prob = my_weight / max(1, char_total)

        # Proba de la rareté
        rarity_items = self.data.rarities
        if force_rare:
            rarity_items = [r for r in rarity_items if r["id"] != "common"]
        rarity_total = sum(r.get("weight", 1) for r in rarity_items)
        rarity_prob = rarity.get("weight", 1) / max(1, rarity_total)

        # Proba de la qualité
        quality_total = sum(q.get("weight", 1) for q in self.data.qualities)
        quality_prob = quality.get("weight", 1) / max(1, quality_total)

        # Proba de la spécialité
        spec_total = sum(s.get("weight", 1) for s in self.data.specialties)
        spec_prob = specialty.get("weight", 1) / max(1, spec_total)

        # Proba de la jewelry
        jew_total = sum(j.get("weight", 1) for j in self.data.jewelries)
        jew_prob = jewelry.get("weight", 1) / max(1, jew_total)

        # Probabilité combinée en % (x10 pour échelle lisible)
        combined = char_prob * rarity_prob * quality_prob * spec_prob * jew_prob * 100 * 10
        return round(combined, 4)

    def _weighted_random(self, items: List[dict],
                          exclude_ids: List[str] = None) -> dict:
        """Sélection aléatoire pondérée parmi une liste d'items."""
        if exclude_ids:
            items = [i for i in items if i["id"] not in exclude_ids]

        if not items:
            return {"id": "unknown", "name": "???", "weight": 1}

        weights = [item.get("weight", 1) for item in items]
        return random.choices(items, weights=weights, k=1)[0]
