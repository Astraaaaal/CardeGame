"""
PackService — Orchestration de l'ouverture de packs.
Toute la logique critique est ici (anti-triche : serveur = autorité).
"""

import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException

from app.models.user import User
from app.models.card import UserCard
from app.models.booster import Booster, BoosterSet
from app.models.reference import Set
from app.models.economy import Resource
from app.services.card_generator import CardGeneratorService
from app.services.card_renderer import CardRendererService
from app.services.wallet import get_balance, apply_delta
from app.services.power import roll_drawn_power, combined_rarity
from app.services import quest_progress
from app.services import activity, guilds, presence_bonus
from app.schemas.card import CardResponse


class PackService:
    """Service d'ouverture de packs — côté serveur uniquement."""

    def __init__(self):
        self.generator = CardGeneratorService()
        self.renderer = CardRendererService()

    async def _booster_set_ids(self, session: AsyncSession, booster: Booster) -> list[str]:
        set_ids = (await session.execute(
            select(BoosterSet.set_id).where(BoosterSet.booster_id == booster.id)
        )).scalars().all()
        return list(set_ids) or [booster.set_id]

    async def generate_and_persist_packs(
        self,
        session: AsyncSession,
        user_id: int,
        booster: Booster,
        quantity: int,
        force_min_rarity_id: Optional[str] = None,
        rarity_weight_multiplier: Optional[float] = None,
        min_quality_id: Optional[str] = None,
        min_jewelry_id: Optional[str] = None,
        specialty_weight_multiplier: Optional[float] = None,
        quality_weight_multiplier: Optional[float] = None,
        jewelry_weight_multiplier: Optional[float] = None,
        power_rolls: Optional[int] = None,
    ) -> tuple[list[list[CardResponse]], int]:
        """
        Génère `quantity` packs pour `booster`, les insère en BDD et retourne
        (packs de CardResponse, nombre total de cartes). Ne touche à aucune
        monnaie — appelant responsable du prix (coins ou ressource).

        `force_min_rarity_id`/`rarity_weight_multiplier` : overrides optionnels
        pour une offre spéciale du shop (cf. CardGeneratorService.generate_pack).
        """
        set_ids = await self._booster_set_ids(session, booster)

        # Bonus de présence (appli restée affichée) : se cumule avec celui de l'offre.
        luck = await presence_bonus.luck_multiplier(session, user_id)
        luck *= await guilds.buff_value(session, user_id, "luck") or 1.0
        if luck > 1.0:
            rarity_weight_multiplier = (rarity_weight_multiplier or 1.0) * luck

        # Seul le nom du set n'est pas déjà porté par card_data (rareté/qualité/
        # spécialité/jewelry viennent enrichis du générateur, cf. `_character` etc.)
        sets_map = await self._load_map(session, Set)

        all_packs_response: list[list[CardResponse]] = []
        total_new_cards = 0

        for _ in range(quantity):
            pack_data = await self.generator.generate_pack(
                session,
                set_ids=set_ids,
                cards_count=booster.cards_count,
                guaranteed_rare=booster.guaranteed_rare,
                force_min_rarity_id=force_min_rarity_id,
                rarity_weight_multiplier=rarity_weight_multiplier,
                force_min_quality_id=min_quality_id,
                force_min_jewelry_id=min_jewelry_id,
                specialty_weight_multiplier=specialty_weight_multiplier,
                quality_weight_multiplier=quality_weight_multiplier,
                jewelry_weight_multiplier=jewelry_weight_multiplier,
            )

            pack_responses = []
            for card_data in pack_data:
                rendered_url = await self.renderer.render_and_upload(session, card_data)
                power = roll_drawn_power(card_data, rolls=power_rolls or 1)

                user_card = UserCard(
                    user_id=user_id,
                    character_id=card_data["character_id"],
                    set_id=card_data["set_id"],
                    rarity_id=card_data["rarity_id"],
                    quality_id=card_data["quality_id"],
                    specialty_id=card_data["specialty_id"],
                    jewelry_id=card_data["jewelry_id"],
                    booster_id=booster.id,
                    drop_probability=card_data["drop_probability"],
                    power=power,
                    rendered_url=rendered_url,
                )
                session.add(user_card)
                total_new_cards += 1

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
                    power=power,
                    combined_rarity=combined_rarity(
                        power, card_data["drop_probability"], card_data["rarity_id"],
                        card_data["quality_id"], card_data["specialty_id"], card_data["jewelry_id"],
                    ),
                    rendered_url=rendered_url,
                    obtained_at=user_card.obtained_at,
                    booster_id=booster.id,
                    booster_name=booster.name,
                    booster_cover_url=booster.cover_image_url or None,
                ))

            all_packs_response.append(pack_responses)

        await quest_progress.increment(session, user_id, "packs_opened", quantity)
        await activity.track_cards_obtained(
            session, user_id, [c.rarity_id for pack in all_packs_response for c in pack],
        )

        return all_packs_response, total_new_cards

    async def charge(
        self, session: AsyncSession, user_id: int, booster_id: str, quantity: int,
    ) -> tuple[Booster, User, int]:
        """Vérifie que le booster est en vente, calcule le prix (réductions
        multi-pack) et débite la monnaie du booster. Ne commit pas."""
        booster = await session.get(Booster, booster_id)
        if not booster:
            raise HTTPException(status_code=404, detail="Booster introuvable")
        if not booster.active or not booster.visible_in_shop:
            raise HTTPException(
                status_code=404,
                detail="Ce booster n'est plus disponible dans la boutique.",
            )

        base_price = booster.price
        if quantity >= 10:
            total_price = math.floor(base_price * quantity * 0.85)
        elif quantity >= 5:
            total_price = math.floor(base_price * quantity * 0.90)
        else:
            total_price = base_price * quantity

        user = await session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")

        have = await get_balance(session, user, booster.resource_id)
        if have < total_price:
            resource = await session.get(Resource, booster.resource_id)
            raise HTTPException(
                status_code=400,
                detail=f"Pas assez de {resource.name if resource else booster.resource_id} "
                       f"({have}/{total_price})",
            )

        await apply_delta(session, user, booster.resource_id, -total_price)
        return booster, user, total_price

    async def open_packs(
        self,
        session: AsyncSession,
        user_id: int,
        booster_id: str,
        quantity: int,
    ) -> dict:
        """
        Ouvre un ou plusieurs packs contre la monnaie du booster (`resource_id`,
        "coins" par défaut) :
        1. Vérifie le booster, 2. calcule le prix (réductions multi-pack),
        3. vérifie/déduit la monnaie, 4. génère + persiste, 5. commit.
        """
        booster, user, total_price = await self.charge(session, user_id, booster_id, quantity)
        user.packs_opened += quantity

        all_packs_response, total_new_cards = await self.generate_and_persist_packs(
            session, user_id, booster, quantity
        )
        user.total_cards += total_new_cards
        await session.commit()

        resource = await session.get(Resource, booster.resource_id)
        return {
            "packs": all_packs_response,
            "total_cost": total_price,
            "remaining_coins": user.coins,
            "resource_id": booster.resource_id,
            "resource_name": resource.name if resource else booster.resource_id,
            "new_balance": await get_balance(session, user, booster.resource_id),
        }

    async def _load_map(self, session: AsyncSession, model) -> dict:
        """Charge tous les enregistrements et retourne un dict id → objet."""
        result = await session.execute(select(model))
        items = result.scalars().all()
        return {item.id: item for item in items}
