"""
Routes shop — offres contre ressources (boosters, cartes précises, upgrades).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.card import UserCard
from app.models.booster import Booster
from app.models.character import Character
from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.models.economy import Resource, UserResource, ShopOffer
from app.schemas.economy import ShopOfferResponse, ShopBuyRequest, ShopBuyResponse
from app.services.pack_service import PackService
from app.services.card_view import build_card_response

router = APIRouter()
pack_service = PackService()


async def _offer_response(session: AsyncSession, o: ShopOffer) -> ShopOfferResponse:
    async def name_of(model, id_):
        if not id_:
            return None
        row = await session.get(model, id_)
        return row.name if row else None

    resource = await session.get(Resource, o.resource_id)
    return ShopOfferResponse(
        id=o.id, kind=o.kind, name=o.name, description=o.description, active=o.active,
        resource_id=o.resource_id, resource_name=resource.name if resource else o.resource_id,
        price=o.price,
        booster_id=o.booster_id,
        character_id=o.character_id, character_name=await name_of(Character, o.character_id),
        rarity_id=o.rarity_id, rarity_name=await name_of(Rarity, o.rarity_id),
        quality_id=o.quality_id, quality_name=await name_of(Quality, o.quality_id),
        specialty_id=o.specialty_id, specialty_name=await name_of(Specialty, o.specialty_id),
        jewelry_id=o.jewelry_id, jewelry_name=await name_of(Jewelry, o.jewelry_id),
        target_quality_id=o.target_quality_id,
        target_quality_name=await name_of(Quality, o.target_quality_id),
        target_specialty_id=o.target_specialty_id,
        target_specialty_name=await name_of(Specialty, o.target_specialty_id),
    )


@router.get("/", response_model=list[ShopOfferResponse])
async def list_offers(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Liste les offres actives du shop."""
    offers = (await session.execute(
        select(ShopOffer).where(ShopOffer.active == True)  # noqa: E712
    )).scalars().all()
    return [await _offer_response(session, o) for o in offers]


@router.post(
    "/buy",
    response_model=ShopBuyResponse,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def buy_offer(
    request: ShopBuyRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Achète une offre du shop contre la ressource requise."""
    offer = await session.get(ShopOffer, request.offer_id)
    if not offer or not offer.active:
        raise HTTPException(status_code=404, detail="Offre introuvable ou inactive.")

    balance = await session.get(UserResource, (user.id, offer.resource_id))
    have = balance.amount if balance else 0
    if have < offer.price:
        resource = await session.get(Resource, offer.resource_id)
        raise HTTPException(
            status_code=400,
            detail=f"Pas assez de {resource.name if resource else offer.resource_id} "
                   f"({have}/{offer.price}).",
        )

    cards_out: list = []

    if offer.kind == "booster":
        booster = await session.get(Booster, offer.booster_id) if offer.booster_id else None
        if not booster:
            raise HTTPException(status_code=500, detail="Booster de l'offre introuvable.")
        packs, new_cards = await pack_service.generate_and_persist_packs(
            session, user.id, booster, quantity=1
        )
        user.packs_opened += 1
        user.total_cards += new_cards
        cards_out = packs[0] if packs else []

    elif offer.kind == "specific_card":
        missing = [
            (label, val) for label, val in [
                ("personnage", offer.character_id), ("rareté", offer.rarity_id),
                ("qualité", offer.quality_id), ("spécialité", offer.specialty_id),
                ("jewelry", offer.jewelry_id),
            ] if not val
        ]
        if missing:
            raise HTTPException(
                status_code=500,
                detail=f"Offre mal configurée (manque : {', '.join(m[0] for m in missing)}).",
            )
        character = await session.get(Character, offer.character_id)
        if not character:
            raise HTTPException(status_code=500, detail="Personnage de l'offre introuvable.")
        # set_id : premier set connu du personnage (peu importe lequel pour un achat direct)
        from app.models.character import CharacterSet
        link = (await session.execute(
            select(CharacterSet).where(CharacterSet.character_id == character.id)
        )).scalars().first()
        card = UserCard(
            user_id=user.id,
            character_id=offer.character_id,
            set_id=link.set_id if link else "",
            rarity_id=offer.rarity_id,
            quality_id=offer.quality_id,
            specialty_id=offer.specialty_id,
            jewelry_id=offer.jewelry_id,
            drop_probability=0.0,  # achat direct, pas un tirage aléatoire
        )
        session.add(card)
        user.total_cards += 1
        await session.flush()
        cards_out = [await build_card_response(session, card)]

    elif offer.kind == "upgrade":
        if not request.card_id:
            raise HTTPException(status_code=400, detail="Choisis la carte à améliorer.")
        card = (await session.execute(
            select(UserCard).where(
                UserCard.id == request.card_id, UserCard.user_id == user.id
            )
        )).scalar_one_or_none()
        if not card:
            raise HTTPException(status_code=404, detail="Carte introuvable.")
        if offer.target_quality_id:
            card.quality_id = offer.target_quality_id
        if offer.target_specialty_id:
            card.specialty_id = offer.target_specialty_id
        session.add(card)
        cards_out = [await build_card_response(session, card)]

    else:
        raise HTTPException(status_code=500, detail=f"Type d'offre inconnu: {offer.kind}")

    if not balance:
        balance = UserResource(user_id=user.id, resource_id=offer.resource_id, amount=0)
        session.add(balance)
    balance.amount -= offer.price

    await session.commit()

    return ShopBuyResponse(
        message=f"« {offer.name} » acheté !",
        resource_id=offer.resource_id,
        new_balance=balance.amount,
        cards=cards_out,
    )
