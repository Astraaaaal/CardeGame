"""
Routes shop — offres contre ressources (boosters, cartes précises, upgrades, reroll).
"""

import random
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.card import UserCard
from app.models.booster import Booster
from app.models.character import Character, CharacterSet
from app.models.reference import Rarity, Quality, Specialty, Jewelry
from app.models.economy import Resource, ShopOffer, ShopPurchase
from app.schemas.economy import ShopOfferResponse, ShopBuyRequest, ShopBuyResponse, ResourceCatalogItem
from app.services.pack_service import PackService
from app.services.card_view import build_card_response
from app.services.daily_feature import get_todays_featured_offer_id
from app.services.tier_order import rank
from app.services.wallet import get_balance, apply_delta

router = APIRouter()
pack_service = PackService()

REROLL_MODELS = {
    "rarity": Rarity, "quality": Quality, "specialty": Specialty, "jewelry": Jewelry,
}


async def _offer_response(
    session: AsyncSession, o: ShopOffer, featured_id: str | None = None, purchases_today: int = 0
) -> ShopOfferResponse:
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
        purchase_limit_per_day=o.purchase_limit_per_day,
        purchases_today=purchases_today,
        is_daily_pool=o.is_daily_pool,
        featured_today=(featured_id is not None and o.id == featured_id),
        booster_id=o.booster_id,
        force_min_rarity_id=o.force_min_rarity_id,
        force_min_rarity_name=await name_of(Rarity, o.force_min_rarity_id),
        rarity_weight_multiplier=o.rarity_weight_multiplier,
        character_id=o.character_id, character_name=await name_of(Character, o.character_id),
        rarity_id=o.rarity_id, rarity_name=await name_of(Rarity, o.rarity_id),
        quality_id=o.quality_id, quality_name=await name_of(Quality, o.quality_id),
        specialty_id=o.specialty_id, specialty_name=await name_of(Specialty, o.specialty_id),
        jewelry_id=o.jewelry_id, jewelry_name=await name_of(Jewelry, o.jewelry_id),
        reroll_rarity=o.reroll_rarity, reroll_quality=o.reroll_quality,
        reroll_specialty=o.reroll_specialty, reroll_jewelry=o.reroll_jewelry,
        reroll_mode=o.reroll_mode,
    )


async def _purchases_today(session: AsyncSession, user_id: int, offer_id: str) -> int:
    start = datetime.combine(date.today(), datetime.min.time())
    return (await session.execute(
        select(func.count()).select_from(ShopPurchase).where(
            ShopPurchase.user_id == user_id,
            ShopPurchase.offer_id == offer_id,
            ShopPurchase.purchased_at >= start,
        )
    )).scalar_one()


@router.get("/", response_model=list[ShopOfferResponse])
async def list_offers(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Liste les offres actives du shop, avec le compteur d'achats du jour."""
    offers = (await session.execute(
        select(ShopOffer).where(ShopOffer.active == True)  # noqa: E712
    )).scalars().all()
    featured_id = await get_todays_featured_offer_id(session)
    out = []
    for o in offers:
        purchases = await _purchases_today(session, user.id, o.id) if o.purchase_limit_per_day else 0
        out.append(await _offer_response(session, o, featured_id, purchases))
    return out


@router.get("/resources", response_model=list[ResourceCatalogItem])
async def list_resources_catalog(
    session: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Catalogue des ressources existantes (id + nom), pour peupler un sélecteur de monnaie côté joueur."""
    rows = (await session.execute(select(Resource).order_by(Resource.name))).scalars().all()
    return [ResourceCatalogItem(id=r.id, name=r.name) for r in rows]


async def _recompute_probability(session: AsyncSession, card: UserCard) -> float:
    """Recalcule drop_probability après un reroll (une ou plusieurs valeurs ont changé)."""
    links = (await session.execute(
        select(CharacterSet).where(CharacterSet.set_id == card.set_id)
    )).scalars().all()
    char_total = sum(l.weight for l in links) or 0
    mine = next((l for l in links if l.character_id == card.character_id), None)
    char_prob = (mine.weight / char_total) if (mine and char_total) else 0.0

    async def frac(model, id_):
        rows = (await session.execute(select(model))).scalars().all()
        total = sum(r.weight for r in rows)
        item = next((r for r in rows if r.id == id_), None)
        return (item.weight / total) if (item and total) else 0.0

    combined = (
        char_prob
        * await frac(Rarity, card.rarity_id)
        * await frac(Quality, card.quality_id)
        * await frac(Specialty, card.specialty_id)
        * await frac(Jewelry, card.jewelry_id)
    )
    return round(combined, 12)


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

    if offer.purchase_limit_per_day:
        done_today = await _purchases_today(session, user.id, offer.id)
        if done_today >= offer.purchase_limit_per_day:
            raise HTTPException(
                status_code=400,
                detail=f"Limite quotidienne atteinte pour « {offer.name} » "
                       f"({done_today}/{offer.purchase_limit_per_day}).",
            )

    have = await get_balance(session, user, offer.resource_id)
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
        if not booster or not booster.active:
            raise HTTPException(status_code=500, detail="Booster de l'offre introuvable ou retiré.")
        packs, new_cards = await pack_service.generate_and_persist_packs(
            session, user.id, booster, quantity=1,
            force_min_rarity_id=offer.force_min_rarity_id,
            rarity_weight_multiplier=offer.rarity_weight_multiplier,
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

    elif offer.kind == "reroll":
        if not request.card_id:
            raise HTTPException(status_code=400, detail="Choisis la carte à retirer.")
        card = (await session.execute(
            select(UserCard).where(
                UserCard.id == request.card_id, UserCard.user_id == user.id
            )
        )).scalar_one_or_none()
        if not card:
            raise HTTPException(status_code=404, detail="Carte introuvable.")

        axes = [
            a for a, on in [
                ("rarity", offer.reroll_rarity), ("quality", offer.reroll_quality),
                ("specialty", offer.reroll_specialty), ("jewelry", offer.reroll_jewelry),
            ] if on
        ]
        if not axes:
            raise HTTPException(status_code=500, detail="Offre de reroll mal configurée (aucun axe).")

        field_map = {"rarity": "rarity_id", "quality": "quality_id",
                     "specialty": "specialty_id", "jewelry": "jewelry_id"}
        for axis in axes:
            model = REROLL_MODELS[axis]
            items = (await session.execute(select(model))).scalars().all()
            pool = items
            if offer.reroll_mode == "guaranteed_min":
                current_id = getattr(card, field_map[axis])
                current_rank = rank(axis, current_id)
                filtered = [i for i in items if rank(axis, i.id) >= current_rank]
                if filtered:
                    pool = filtered
            weights = [i.weight for i in pool]
            picked = random.choices(pool, weights=weights, k=1)[0]
            setattr(card, field_map[axis], picked.id)

        card.drop_probability = await _recompute_probability(session, card)
        session.add(card)
        cards_out = [await build_card_response(session, card)]

    else:
        raise HTTPException(status_code=500, detail=f"Type d'offre inconnu: {offer.kind}")

    new_balance = await apply_delta(session, user, offer.resource_id, -offer.price)
    session.add(ShopPurchase(user_id=user.id, offer_id=offer.id))

    await session.commit()

    return ShopBuyResponse(
        message=f"« {offer.name} » acheté !",
        resource_id=offer.resource_id,
        new_balance=new_balance,
        cards=cards_out,
    )
