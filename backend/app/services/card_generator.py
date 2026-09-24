"""
CardGeneratorService — Génération pondérée de cartes.
Migration directe de src/engine/card_generator.py mais avec la BDD.
"""

import random
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.models.character import Character, CharacterSet
from app.services.power import REFERENCE_SET_SIZE
from app.services.tier_order import rank


def merge_full_art(specialties, weights: list[float]) -> list[float]:
    """Poids des spécialités pour un personnage SANS full art : la part du full
    art s'ajoute à « normale » (tirer full art = carte sans spécialité)."""
    full_art = sum(w for sp, w in zip(specialties, weights, strict=True) if sp.id == "full_art")
    return [0.0 if sp.id == "full_art" else w + (full_art if sp.id == "normal" else 0)
            for sp, w in zip(specialties, weights, strict=True)]


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
        force_min_quality_id: Optional[str] = None,
        force_min_jewelry_id: Optional[str] = None,
        specialty_weight_multiplier: Optional[float] = None,
        quality_weight_multiplier: Optional[float] = None,
        jewelry_weight_multiplier: Optional[float] = None,
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
                min_quality_id=force_min_quality_id if is_last else None,
                min_jewelry_id=force_min_jewelry_id if is_last else None,
                specialty_weight_multiplier=specialty_weight_multiplier,
                quality_weight_multiplier=quality_weight_multiplier,
                jewelry_weight_multiplier=jewelry_weight_multiplier,
            )
            cards.append(card)

        return cards

    def _generate_single(
        self,
        characters: list[dict],
        rarities: list,
        qualities: list,
        specialties: list,
        jewelries: list,
        min_rarity_id: Optional[str] = None,
        rarity_weight_multiplier: Optional[float] = None,
        min_quality_id: Optional[str] = None,
        min_jewelry_id: Optional[str] = None,
        specialty_weight_multiplier: Optional[float] = None,
        quality_weight_multiplier: Optional[float] = None,
        jewelry_weight_multiplier: Optional[float] = None,
    ) -> dict:
        """Génère une seule carte aléatoire."""
        # 1. Personnage pondéré. Chaque entrée = un lien (personnage, set) : un
        #    personnage présent dans plusieurs des sets du booster a d'autant
        #    plus de "tickets" dans le tirage (poids additifs, naturellement).
        char_weights = [c["weight"] for c in characters]
        character = random.choices(characters, weights=char_weights, k=1)[0]

        # 2 à 5. Chaque axe est tiré NORMALEMENT (poids éventuellement boostés
        #    par la chance) ; un minimum garanti (booster, offre, machine) ne fait
        #    que REMONTER le résultat s'il tombe en dessous : les paliers
        #    au-dessus du minimum gardent leur chance de base (une légendaire
        #    reste à ~0,5 % dans un booster « épique garanti »).
        def boosted(items, multiplier, better):
            return [i.weight * (multiplier if multiplier and better(i) else 1) for i in items]

        def base_weights(items):
            return [i.weight for i in items]

        # Personnage sans version full art : un tirage « full art » donne une
        # carte sans spécialité (sa part du tirage revient à « normale »).
        specialty_weights = boosted(specialties, specialty_weight_multiplier, lambda sp: sp.id != "normal")
        specialty_base = base_weights(specialties)
        if not character.get("full_art"):
            specialty_weights = merge_full_art(specialties, specialty_weights)
            specialty_base = merge_full_art(specialties, specialty_base)

        axes = [
            ("rarity", rarities, min_rarity_id,
             boosted(rarities, rarity_weight_multiplier, lambda r: r.id != "common")),
            ("quality", qualities, min_quality_id,
             boosted(qualities, quality_weight_multiplier, lambda q: rank("quality", q.id) >= rank("quality", "preserved"))),
            ("specialty", specialties, None, specialty_weights),
            ("jewelry", jewelries, min_jewelry_id,
             boosted(jewelries, jewelry_weight_multiplier, lambda j: j.id != "none")),
        ]
        picked = {axis: self._floor_pick(items, weights, axis, min_id) for axis, items, min_id, weights in axes}
        rarity, quality, specialty, jewelry = picked["rarity"], picked["quality"], picked["specialty"], picked["jewelry"]

        # 6. Probabilités : celle du tirage réel (chance comprise) et celle de BASE
        #    (son set seul, poids normaux) qui fixe la puissance maximum et reste
        #    affichée. Dans les deux, un axe garanti ne compte, s'il est resté au
        #    minimum, que pour sa chance d'être « au plus » ce minimum (≈ certaine) :
        #    une garantie rend la carte facile, donc moins puissante.
        def char_prob(pool):
            total = sum(c["weight"] for c in pool)
            return character["weight"] / total if total else 0.0

        same_set = [c for c in characters if c["set_id"] == character["set_id"]]
        draw_prob = char_prob(characters)
        drop_prob = char_prob(same_set)
        # Probabilité qui fixe la PLAGE DE PUISSANCE : même calcul, mais le
        # facteur « quel personnage » est ramené à un set de référence. Sans
        # ça, agrandir un set rendrait toutes ses cartes plus puissantes, pour
        # une rareté que le joueur ne perçoit pas.
        power_prob = 1.0 / REFERENCE_SET_SIZE
        # Sa jumelle « chance comprise » : même base de référence, axes boostés.
        # Les deux ne diffèrent donc QUE par la chance du moment — sans ça, un
        # booster couvrant plus de dix personnages élargissait la plage de
        # tirage à lui seul et sortait la moitié des cartes au maximum.
        power_draw_prob = 1.0 / REFERENCE_SET_SIZE
        for axis, items, min_id, weights in axes:
            draw_prob *= self._axis_factor(items, weights, axis, picked[axis], min_id)
            power_draw_prob *= self._axis_factor(items, weights, axis, picked[axis], min_id, True)
            base = specialty_base if axis == "specialty" else base_weights(items)
            drop_prob *= self._axis_factor(items, base, axis, picked[axis], min_id)
            power_prob *= self._axis_factor(items, base, axis, picked[axis], min_id, True)

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
            "draw_probability": draw_prob,
            "power_probability": power_prob,
            "power_draw_probability": power_draw_prob,
            # Données enrichies pour la réponse
            "_character": character,
            "_rarity": rarity,
            "_quality": quality,
            "_specialty": specialty,
            "_jewelry": jewelry,
        }

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
                "full_art": char.full_art,
                "full_art_image_url": char.full_art_image_url,
                "weight": weight,
                "set_id": set_id,
            })
        return chars

    async def _get_all(self, session: AsyncSession, model):
        """Charge tous les enregistrements d'une table de référence."""
        result = await session.execute(select(model))
        return result.scalars().all()

    @staticmethod
    def _floor_pick(items, weights, axis: str, min_id: Optional[str]):
        """Tirage pondéré normal, remonté au minimum garanti s'il tombe en dessous."""
        item = random.choices(items, weights=weights, k=1)[0]
        if min_id and rank(axis, item.id) < rank(axis, min_id):
            item = next((i for i in items if i.id == min_id), item)
        return item

    @staticmethod
    def _axis_factor(items, weights, axis: str, item, min_id: Optional[str],
                     garantie_neutre: bool = False) -> float:
        """Chance de ce résultat sur l'axe : au minimum garanti, somme des paliers
        qui y sont remontés (lui compris) ; sinon sa propre chance.

        `garantie_neutre` : réservé au calcul de la PUISSANCE. Un palier garanti
        absorbe tout ce qui est en dessous de lui, ce qui rend la carte presque
        certaine — et donc très faible. L'ampleur du coup dépendait alors de la
        forme de l'échelle : la rareté et le bijou ont un palier du bas qui pèse
        déjà 95 % et plus, donc la garantie n'y changeait presque rien, tandis
        que la qualité étale son poids sur cinq paliers bas et s'effondrait
        (médiane 7 contre 39). Plafonner l'absorption à ce que vaut un tirage
        MOYEN sur l'axe rend la garantie neutre sur la puissance, de la même
        façon sur les trois axes : elle change ce qu'on obtient, pas ce que ça
        vaut. La rareté AFFICHÉE, elle, garde l'absorption complète : une carte
        garantie est bel et bien facile à obtenir, et doit le dire."""
        total = sum(weights)
        if not total:
            return 0.0
        if min_id and item.id == min_id:
            floor = rank(axis, min_id)
            absorbe = sum(w for i, w in zip(items, weights, strict=True) if rank(axis, i.id) <= floor)
            if garantie_neutre:
                absorbe = min(absorbe, sum(w * w for w in weights) / total)
            return absorbe / total
        return next((w for i, w in zip(items, weights, strict=True) if i.id == item.id), 0) / total
