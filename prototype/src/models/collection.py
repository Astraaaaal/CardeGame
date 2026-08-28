"""
Modèle Collection — Stocke toutes les cartes du joueur.
Gère l'ajout, la suppression, le filtrage et le tri.
"""

from typing import List, Optional
from .card import Card


class Collection:
    """Collection de cartes du joueur."""

    def __init__(self):
        self.cards: List[Card] = []

    def add_card(self, card: Card):
        """Ajoute une carte à la collection."""
        self.cards.append(card)

    def add_cards(self, cards: List[Card]):
        """Ajoute plusieurs cartes à la collection."""
        self.cards.extend(cards)

    def remove_card(self, uid: str) -> Optional[Card]:
        """Retire une carte par son UID et la retourne."""
        for i, card in enumerate(self.cards):
            if card.uid == uid:
                return self.cards.pop(i)
        return None

    def get_card(self, uid: str) -> Optional[Card]:
        """Récupère une carte par son UID."""
        for card in self.cards:
            if card.uid == uid:
                return card
        return None

    def count(self) -> int:
        """Nombre total de cartes."""
        return len(self.cards)

    def filter_by_set(self, set_id: str) -> List[Card]:
        """Filtre les cartes par set."""
        return [c for c in self.cards if c.set_id == set_id]

    def filter_by_rarity(self, rarity_id: str) -> List[Card]:
        """Filtre les cartes par rareté."""
        return [c for c in self.cards if c.rarity_id == rarity_id]

    def filter_by_character(self, character_id: str) -> List[Card]:
        """Filtre les cartes par personnage."""
        return [c for c in self.cards if c.character_id == character_id]

    def filter_by_specialty(self, specialty_id: str) -> List[Card]:
        """Filtre les cartes par spécialité."""
        return [c for c in self.cards if c.specialty_id == specialty_id]

    def sort_by_name(self, reverse: bool = False) -> List[Card]:
        """Trie les cartes par nom."""
        return sorted(self.cards, key=lambda c: c.name, reverse=reverse)

    def sort_by_rarity(self, reverse: bool = True) -> List[Card]:
        """Trie par rareté (légendaire en premier par défaut)."""
        rarity_order = {
            "legendary": 4, "epic": 3, "rare": 2, "common": 1
        }
        return sorted(
            self.cards,
            key=lambda c: rarity_order.get(c.rarity_id, 0),
            reverse=reverse
        )

    def sort_by_quality(self, reverse: bool = False) -> List[Card]:
        """Trie par qualité (meilleure qualité en premier par défaut)."""
        quality_order = {
            "authentic": 14, "mint": 13, "graded": 12, "excellent": 11,
            "preserved": 10, "fair": 9, "worn": 8, "faded": 7,
            "scratched": 6, "torn": 5, "damaged": 4,
            "Unplayable": 3, "Unreadable": 2, "destroyed": 1,
        }
        return sorted(
            self.cards,
            key=lambda c: quality_order.get(c.quality_id, 0),
            reverse=not reverse  # reverse=False → meilleure d'abord
        )

    def sort_by_specialty(self, reverse: bool = True) -> List[Card]:
        """Trie par spécialité (la plus rare en premier par défaut)."""
        specialty_order = {
            "ex": 4, "shiny": 3, "full_art": 2, "normal": 1,
        }
        return sorted(
            self.cards,
            key=lambda c: specialty_order.get(c.specialty_id, 0),
            reverse=reverse
        )

    def sort_by_jewelry(self, reverse: bool = True) -> List[Card]:
        """Trie par jewelry (la plus rare en premier par défaut)."""
        jewelry_order = {
            "prismatic": 5, "diamond": 4, "gold": 3, "silver": 2, "none": 1,
        }
        return sorted(
            self.cards,
            key=lambda c: jewelry_order.get(c.jewelry_id, 0),
            reverse=reverse
        )

    def sort_by_probability(self, reverse: bool = False) -> List[Card]:
        """Trie par probabilité d'obtention (plus rare en premier par défaut)."""
        return sorted(
            self.cards,
            key=lambda c: c.drop_probability,
            reverse=reverse
        )

    def get_unique_characters(self) -> List[str]:
        """Liste des personnages uniques possédés."""
        return list(set(c.character_id for c in self.cards))

    def to_dict_list(self) -> list:
        """Sérialise pour sauvegarde."""
        return [card.to_dict() for card in self.cards]

    @classmethod
    def from_dict_list(cls, data: list) -> "Collection":
        """Charge depuis une liste de dictionnaires."""
        collection = cls()
        for card_data in data:
            collection.add_card(Card.from_dict(card_data))
        return collection
