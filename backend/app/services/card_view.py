"""
Construction d'un CardResponse enrichi à partir d'un UserCard — factorisé pour
être réutilisé par la collection, le shop, etc.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import UserCard
from app.models.character import Character
from app.models.booster import Booster
from app.models.reference import Set, Rarity, Quality, Specialty, Jewelry
from app.schemas.card import CardResponse


async def build_card_response(session: AsyncSession, card: UserCard) -> CardResponse:
    char = await session.get(Character, card.character_id)
    set_info = await session.get(Set, card.set_id)
    rarity = await session.get(Rarity, card.rarity_id)
    quality = await session.get(Quality, card.quality_id)
    specialty = await session.get(Specialty, card.specialty_id)
    jewelry = await session.get(Jewelry, card.jewelry_id)
    booster = await session.get(Booster, card.booster_id) if card.booster_id else None

    return CardResponse(
        id=card.id,
        character_id=card.character_id,
        character_name=char.name if char else "",
        character_type=char.type if char else "",
        character_description=char.description if char else "",
        gen=char.gen if char else 1,
        image_url=char.image_url if char else "",
        set_id=card.set_id,
        set_name=set_info.name if set_info else card.set_id,
        rarity_id=card.rarity_id,
        rarity_name=rarity.name if rarity else "",
        rarity_color=rarity.color if rarity else [200, 200, 200],
        quality_id=card.quality_id,
        quality_name=quality.name if quality else "",
        specialty_id=card.specialty_id,
        specialty_name=specialty.name if specialty else "",
        jewelry_id=card.jewelry_id,
        jewelry_name=jewelry.name if jewelry else "Commune",
        jewelry_color=jewelry.color if jewelry else [100, 100, 120],
        drop_probability=card.drop_probability,
        rendered_url=card.rendered_url,
        obtained_at=card.obtained_at,
        booster_id=card.booster_id,
        booster_name=booster.name if booster else None,
        booster_cover_url=booster.cover_image_url if booster and booster.cover_image_url else None,
    )
