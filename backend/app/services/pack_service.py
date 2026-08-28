"""
PackService — Orchestration de l'ouverture de packs.
Toute la logique critique est ici (anti-triche : serveur = autorité).
"""

import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException

from app.models.user import User
from app.models.card import UserCard
from app.models.booster import Booster
from app.models.reference import Rarity, Quality, Specialty, Jewelry, Set
from app.models.character import Character
from app.services.card_generator import CardGeneratorService
from app.services.card_renderer import CardRendererService
from app.schemas.card import CardResponse


class PackService:
    """Service d'ouverture de packs — côté serveur uniquement."""

    def __init__(self):
        self.generator = CardGeneratorService()
        self.renderer = CardRendererService()

    async def open_packs(
        self,
        session: AsyncSession,
        user_id: int,
        booster_id: str,
        quantity: int,
    ) -> dict:
        """
        Ouvre un ou plusieurs packs :
        1. Vérifie le booster
        2. Calcule le prix (réductions multi-pack)
        3. Vérifie et déduit les coins
        4. Génère les cartes
        5. Rend les images
        6. Insère en BDD
        """
        # 1. Charger le booster
        booster = await session.get(Booster, booster_id)
        if not booster:
            raise HTTPException(status_code=404, detail="Booster introuvable")

        # 2. Calcul du prix (x5=-10%, x10=-15%)
        base_price = booster.price
        if quantity >= 10:
            total_price = math.floor(base_price * quantity * 0.85)
        elif quantity >= 5:
            total_price = math.floor(base_price * quantity * 0.90)
        else:
            total_price = base_price * quantity

        # 3. Vérifier les coins
        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        if user.coins < total_price:
            raise HTTPException(
                status_code=400,
                detail=f"Pas assez de pièces ({user.coins}/{total_price})",
            )

        # 4. Déduire les coins AVANT génération (atomicité)
        user.coins -= total_price
        user.packs_opened += quantity

        # 5. Générer toutes les cartes
        all_packs_response: list[list[CardResponse]] = []
        total_new_cards = 0

        # Pré-charger les tables de référence pour enrichir les réponses
        sets_map = await self._load_map(session, Set)
        rarities_map = await self._load_map(session, Rarity)
        qualities_map = await self._load_map(session, Quality)
        specialties_map = await self._load_map(session, Specialty)
        jewelries_map = await self._load_map(session, Jewelry)

        for _ in range(quantity):
            pack_data = await self.generator.generate_pack(
                session,
                set_id=booster.set_id,
                cards_count=booster.cards_count,
                guaranteed_rare=booster.guaranteed_rare,
            )

            pack_responses = []
            for card_data in pack_data:
                # Rendre l'image
                rendered_url = await self.renderer.render_and_upload(
                    session, card_data
                )

                # Créer en BDD
                user_card = UserCard(
                    user_id=user_id,
                    character_id=card_data["character_id"],
                    set_id=card_data["set_id"],
                    rarity_id=card_data["rarity_id"],
                    quality_id=card_data["quality_id"],
                    specialty_id=card_data["specialty_id"],
                    jewelry_id=card_data["jewelry_id"],
                    drop_probability=card_data["drop_probability"],
                    rendered_url=rendered_url,
                )
                session.add(user_card)
                total_new_cards += 1

                # Construire la réponse enrichie
                char = card_data.get("_character", {})
                rarity = card_data.get("_rarity")
                quality = card_data.get("_quality")
                specialty = card_data.get("_specialty")
                jewelry = card_data.get("_jewelry")
                set_info = sets_map.get(card_data["set_id"])

                pack_responses.append(CardResponse(
                    id=user_card.id,
                    character_id=char.get("id", ""),
                    character_name=char.get("name", ""),
                    character_type=char.get("type", ""),
                    character_description=char.get("description", ""),
                    gen=char.get("gen", 1),
                    image_url=char.get("image_url", ""),
                    set_id=card_data["set_id"],
                    set_name=set_info.name if set_info else card_data["set_id"],
                    rarity_id=rarity.id if rarity else "",
                    rarity_name=rarity.name if rarity else "",
                    rarity_color=rarity.color if rarity else [200, 200, 200],
                    quality_id=quality.id if quality else "",
                    quality_name=quality.name if quality else "",
                    specialty_id=specialty.id if specialty else "",
                    specialty_name=specialty.name if specialty else "",
                    jewelry_id=jewelry.id if jewelry else "none",
                    jewelry_name=jewelry.name if jewelry else "Commune",
                    jewelry_color=jewelry.color if jewelry else [100, 100, 120],
                    drop_probability=card_data["drop_probability"],
                    rendered_url=rendered_url,
                    obtained_at=user_card.obtained_at,
                ))

            all_packs_response.append(pack_responses)

        user.total_cards += total_new_cards
        await session.commit()

        return {
            "packs": all_packs_response,
            "total_cost": total_price,
            "remaining_coins": user.coins,
        }

    async def _load_map(self, session: AsyncSession, model) -> dict:
        """Charge tous les enregistrements et retourne un dict id → objet."""
        result = await session.execute(select(model))
        items = result.scalars().all()
        return {item.id: item for item in items}
