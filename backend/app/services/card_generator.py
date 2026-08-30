"""
CardGeneratorService — Génération pondérée de cartes.
Migration directe de src/engine/card_generator.py mais avec la BDD.
"""

import random
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.models.character import Character, CharacterSet


class CardGeneratorService:
    """Génère des cartes avec tirage aléatoire pondéré (côté serveur = anti-triche)."""

    async def generate_pack(
        self,
        session: AsyncSession,
        set_id: str,
        cards_count: int,
        guaranteed_rare: bool,
    ) -> list[dict]:
        """Génère un pack complet de cartes."""
        # Charger les données depuis la BDD
        characters = await self._get_characters_for_set(session, set_id)
        rarities = await self._get_all(session, Rarity)
        qualities = await self._get_all(session, Quality)
        specialties = await self._get_all(session, Specialty)
        jewelries = await self._get_all(session, Jewelry)

        if not characters:
            return []

        cards = []
        for i in range(cards_count):
            force_rare = guaranteed_rare and i == cards_count - 1
            card = self._generate_single(
                characters, set_id, rarities, qualities,
                specialties, jewelries, force_rare,
            )
            cards.append(card)

        return cards

    def _generate_single(
        self,
        characters: list[dict],
        set_id: str,
        rarities: list,
        qualities: list,
        specialties: list,
        jewelries: list,
        force_rare: bool = False,
    ) -> dict:
        """Génère une seule carte aléatoire."""
        # 1. Personnage pondéré
        char_weights = [c["weight"] for c in characters]
        character = random.choices(characters, weights=char_weights, k=1)[0]

        # 2. Rareté
        rarity_pool = (
            [r for r in rarities if r.id != "common"] if force_rare else rarities
        )
        rarity = self._weighted_pick(rarity_pool)

        # 3. Qualité
        quality = self._weighted_pick(qualities)

        # 4. Spécialité
        specialty = self._weighted_pick(specialties)

        # 5. Jewelry
        jewelry = self._weighted_pick(jewelries)

        # 6. Probabilité combinée
        drop_prob = self._calculate_probability(
            characters, character, rarity, quality, specialty, jewelry,
            force_rare, rarities, qualities, specialties, jewelries,
        )

        return {
            "character_id": character["id"],
            "set_id": set_id,
            "rarity_id": rarity.id,
            "quality_id": quality.id,
            "specialty_id": specialty.id,
            "jewelry_id": jewelry.id,
            "drop_probability": drop_prob,
            # Données enrichies pour la réponse
            "_character": character,
            "_rarity": rarity,
            "_quality": quality,
            "_specialty": specialty,
            "_jewelry": jewelry,
        }

    def _calculate_probability(
        self,
        characters: list[dict],
        character: dict,
        rarity,
        quality,
        specialty,
        jewelry,
        force_rare: bool,
        all_rarities: list,
        all_qualities: list,
        all_specialties: list,
        all_jewelries: list,
    ) -> float:
        """
        Probabilité RÉELLE (entre 0 et 1) de tirer exactement cette combinaison,
        = produit des probabilités marginales (poids / somme des poids) de chaque
        axe. Le client l'affiche en « 1 sur N ».
        """
        def frac(item, pool) -> float:
            total = sum(x.weight for x in pool)
            return (item.weight / total) if total else 0.0

        char_total = sum(c["weight"] for c in characters)
        char_prob = (character["weight"] / char_total) if char_total else 0.0

        rarity_pool = (
            [r for r in all_rarities if r.id != "common"]
            if force_rare
            else all_rarities
        )

        combined = (
            char_prob
            * frac(rarity, rarity_pool)
            * frac(quality, all_qualities)
            * frac(specialty, all_specialties)
            * frac(jewelry, all_jewelries)
        )
        return round(combined, 12)

    async def _get_characters_for_set(
        self, session: AsyncSession, set_id: str
    ) -> list[dict]:
        """Récupère les personnages d'un set avec leurs poids."""
        result = await session.execute(
            select(Character, CharacterSet.weight)
            .join(CharacterSet, Character.id == CharacterSet.character_id)
            .where(CharacterSet.set_id == set_id)
        )
        chars = []
        for char, weight in result.all():
            chars.append({
                "id": char.id,
                "name": char.name,
                "description": char.description,
                "type": char.type,
                "gen": char.gen,
                "image_url": char.image_url,
                "weight": weight,
            })
        return chars

    async def _get_all(self, session: AsyncSession, model):
        """Charge tous les enregistrements d'une table de référence."""
        result = await session.execute(select(model))
        return result.scalars().all()

    @staticmethod
    def _weighted_pick(items):
        weights = [item.weight for item in items]
        return random.choices(items, weights=weights, k=1)[0]
