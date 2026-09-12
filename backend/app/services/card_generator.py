"""
CardGeneratorService — Génération pondérée de cartes.
Migration directe de src/engine/card_generator.py mais avec la BDD.
"""

import random
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.models.character import Character, CharacterSet
from app.services.tier_order import rank


class CardGeneratorService:
    """Génère des cartes avec tirage aléatoire pondéré (côté serveur = anti-triche)."""

    async def generate_pack(
        self,
        session: AsyncSession,
        set_ids: list[str],
        cards_count: int,
        guaranteed_rare: bool,
        force_min_rarity_id: Optional[str] = None,
        rarity_weight_multiplier: Optional[float] = None,
    ) -> list[dict]:
        """
        Génère un pack complet de cartes, en piochant dans un ou plusieurs sets.

        `force_min_rarity_id` et `rarity_weight_multiplier` sont des overrides
        optionnels, utilisés par les offres spéciales du shop à ressources
        (ex: "booster du jour") — ils n'affectent PAS l'ouverture normale d'un
        booster en pièces, qui ne passe que `guaranteed_rare`.
        - `force_min_rarity_id` : comme `guaranteed_rare`, mais avec un palier
          choisi (ex: "epic") au lieu de "pas commune" — s'applique à la
          dernière carte du pack.
        - `rarity_weight_multiplier` : multiplie le poids de TOUTES les raretés
          non-communes, pour TOUTES les cartes du pack (décale la distribution
          entière plutôt que de garantir une seule carte).
        """
        characters = await self._get_characters_for_sets(session, set_ids)
        rarities = await self._get_all(session, Rarity)
        qualities = await self._get_all(session, Quality)
        specialties = await self._get_all(session, Specialty)
        jewelries = await self._get_all(session, Jewelry)

        if not characters:
            return []

        cards = []
        for i in range(cards_count):
            is_last = i == cards_count - 1
            min_rarity_id = force_min_rarity_id if (force_min_rarity_id and is_last) else (
                "rare" if (guaranteed_rare and is_last) else None
            )
            card = self._generate_single(
                characters, rarities, qualities, specialties, jewelries,
                min_rarity_id=min_rarity_id,
                rarity_weight_multiplier=rarity_weight_multiplier,
            )
            cards.append(card)

        return cards

    def _rarity_pool_and_weights(
        self,
        rarities: list,
        min_rarity_id: Optional[str],
        rarity_weight_multiplier: Optional[float],
    ) -> tuple[list, list[float]]:
        pool = rarities
        if min_rarity_id:
            min_rank = rank("rarity", min_rarity_id)
            filtered = [r for r in pool if rank("rarity", r.id) >= min_rank]
            if filtered:
                pool = filtered
        weights = [
            r.weight * rarity_weight_multiplier
            if (rarity_weight_multiplier and r.id != "common") else r.weight
            for r in pool
        ]
        return pool, weights

    def _generate_single(
        self,
        characters: list[dict],
        rarities: list,
        qualities: list,
        specialties: list,
        jewelries: list,
        min_rarity_id: Optional[str] = None,
        rarity_weight_multiplier: Optional[float] = None,
    ) -> dict:
        """Génère une seule carte aléatoire."""
        # 1. Personnage pondéré. Chaque entrée = un lien (personnage, set) : un
        #    personnage présent dans plusieurs des sets du booster a d'autant
        #    plus de "tickets" dans le tirage (poids additifs, naturellement).
        char_weights = [c["weight"] for c in characters]
        character = random.choices(characters, weights=char_weights, k=1)[0]

        # 2. Rareté (pool + poids éventuellement ajustés par l'offre)
        rarity_pool, rarity_weights = self._rarity_pool_and_weights(
            rarities, min_rarity_id, rarity_weight_multiplier
        )
        rarity = random.choices(rarity_pool, weights=rarity_weights, k=1)[0]

        # 3. Qualité
        quality = self._weighted_pick(qualities)

        # 4. Spécialité
        specialty = self._weighted_pick(specialties)

        # 5. Jewelry
        jewelry = self._weighted_pick(jewelries)

        # 6. Probabilité combinée (avec le même pool/poids ajustés que le tirage)
        drop_prob = self._calculate_probability(
            characters, character, rarity, quality, specialty, jewelry,
            rarity_pool, rarity_weights, qualities, specialties, jewelries,
        )

        return {
            "character_id": character["id"],
            # Le set attribué à la carte est celui du lien (personnage, set)
            # effectivement tiré — pas "le" set du booster, qui peut en avoir plusieurs.
            "set_id": character["set_id"],
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
        rarity_pool: list,
        rarity_weights: list[float],
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

        rarity_total = sum(rarity_weights)
        rarity_idx = rarity_pool.index(rarity)
        rarity_prob = (rarity_weights[rarity_idx] / rarity_total) if rarity_total else 0.0

        combined = (
            char_prob
            * rarity_prob
            * frac(quality, all_qualities)
            * frac(specialty, all_specialties)
            * frac(jewelry, all_jewelries)
        )
        return round(combined, 12)

    async def _get_characters_for_sets(
        self, session: AsyncSession, set_ids: list[str]
    ) -> list[dict]:
        """
        Récupère les personnages disponibles dans les sets donnés, une entrée
        par lien (personnage, set) — un personnage lié à plusieurs de ces sets
        apparaît plusieurs fois, avec le poids et le set de CE lien précis.
        """
        result = await session.execute(
            select(Character, CharacterSet.weight, CharacterSet.set_id)
            .join(CharacterSet, Character.id == CharacterSet.character_id)
            .where(CharacterSet.set_id.in_(set_ids))
        )
        chars = []
        for char, weight, set_id in result.all():
            chars.append({
                "id": char.id,
                "name": char.name,
                "description": char.description,
                "type": char.type,
                "gen": char.gen,
                "image_url": char.image_url,
                "weight": weight,
                "set_id": set_id,
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
