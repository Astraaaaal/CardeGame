"""
DataManager — Charge et gère toutes les données JSON du jeu.
Point central pour accéder aux personnages, sets, raretés, qualités,
spécialités et boosters. Facilement extensible.
"""

import json
import os
from typing import Dict, List, Optional
from ..utils.constants import DATA_DIR


class DataManager:
    """Gestionnaire centralisé de toutes les données du jeu."""

    def __init__(self):
        self.characters: List[dict] = []
        self.sets: List[dict] = []
        self.rarities: List[dict] = []
        self.qualities: List[dict] = []
        self.specialties: List[dict] = []
        self.jewelries: List[dict] = []
        self.boosters: List[dict] = []

        # Index rapides par id
        self._characters_by_id: Dict[str, dict] = {}
        self._sets_by_id: Dict[str, dict] = {}
        self._rarities_by_id: Dict[str, dict] = {}
        self._qualities_by_id: Dict[str, dict] = {}
        self._specialties_by_id: Dict[str, dict] = {}
        self._jewelries_by_id: Dict[str, dict] = {}
        self._boosters_by_id: Dict[str, dict] = {}

    def load_all(self):
        """Charge toutes les données depuis les fichiers JSON."""
        self.characters = self._load_json("characters.json", "characters")
        self.sets = self._load_json("sets.json", "sets")
        self.rarities = self._load_json("rarities.json", "rarities")
        self.qualities = self._load_json("qualities.json", "qualities")
        self.specialties = self._load_json("specialties.json", "specialties")
        self.jewelries = self._load_json("jewelries.json", "jewelries")
        self.boosters = self._load_json("boosters.json", "boosters")

        # Construire les index
        self._characters_by_id = {c["id"]: c for c in self.characters}
        self._sets_by_id = {s["id"]: s for s in self.sets}
        self._rarities_by_id = {r["id"]: r for r in self.rarities}
        self._qualities_by_id = {q["id"]: q for q in self.qualities}
        self._specialties_by_id = {s["id"]: s for s in self.specialties}
        self._jewelries_by_id = {j["id"]: j for j in self.jewelries}
        self._boosters_by_id = {b["id"]: b for b in self.boosters}

        print(f"[DataManager] Chargé: {len(self.characters)} personnages, "
              f"{len(self.sets)} sets, {len(self.rarities)} raretés, "
              f"{len(self.qualities)} qualités, {len(self.specialties)} spécialités, "
              f"{len(self.jewelries)} jewelries, "
              f"{len(self.boosters)} boosters")

    def _load_json(self, filename: str, key: str) -> list:
        """Charge un fichier JSON et retourne la liste sous la clé donnée."""
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"[DataManager] ATTENTION: {filepath} introuvable!")
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get(key, [])
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[DataManager] Erreur lecture {filename}: {e}")
            return []

    # --- Accesseurs par ID ---

    def get_character(self, char_id: str) -> Optional[dict]:
        return self._characters_by_id.get(char_id)

    def get_set(self, set_id: str) -> Optional[dict]:
        return self._sets_by_id.get(set_id)

    def get_rarity(self, rarity_id: str) -> Optional[dict]:
        return self._rarities_by_id.get(rarity_id)

    def get_quality(self, quality_id: str) -> Optional[dict]:
        return self._qualities_by_id.get(quality_id)

    def get_specialty(self, specialty_id: str) -> Optional[dict]:
        return self._specialties_by_id.get(specialty_id)

    def get_jewelry(self, jewelry_id: str) -> Optional[dict]:
        return self._jewelries_by_id.get(jewelry_id)

    def get_booster(self, booster_id: str) -> Optional[dict]:
        return self._boosters_by_id.get(booster_id)

    # --- Filtres ---

    def get_characters_for_set(self, set_id: str) -> List[dict]:
        """Retourne les personnages disponibles dans un set donné."""
        return [c for c in self.characters if set_id in c.get("sets", [])]

    def get_booster_for_set(self, set_id: str) -> Optional[dict]:
        """Retourne le booster correspondant à un set."""
        for b in self.boosters:
            if b.get("set") == set_id:
                return b
        return None
