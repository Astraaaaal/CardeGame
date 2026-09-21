"""
Routes shop — offres contre ressources (boosters, cartes précises, upgrades, reroll).
"""

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
from app.schemas.economy import (
    ShopOfferResponse, ShopBuyRequest, ShopBuyResponse, ResourceCatalogItem,
    RerollTokenOut, RerollUseRequest, RerollUseResponse,
)
from app.services.pack_service import PackService
from app.services.card_view import build_card_response
from app.services.daily_feature import get_todays_featured_offer_id
from app.services.wallet import get_balance, apply_delta
from app.services.ranking import refresh_all_best_ranks
from app.services import activity, booster_inventory, expeditions, purchase_limits, quest_progress, reroll_inventory
from app.services.reroll import apply_reroll, assign_bought_card_power
from app.services import premium as premium_svc
from app.models.premium import Cosmetic
from app.services import unlocks
from app.services.wallet import require_balance

router = APIRouter()
pack_service = PackService()


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
        limit_period=_limit_period(o), limit_count=_limit_count(o),
        purchases_in_period=purchases_today,
        grants=[{**g, "name": await _grant_name(session, g["kind"], g["id"])} for g in (o.grants or [])],
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
        reroll_power=o.reroll_power,
        reroll_mode=o.reroll_mode,
        cosmetic_id=o.cosmetic_id, cosmetic_name=await name_of(Cosmetic, o.cosmetic_id),
        card_power_mode=o.card_power_mode, card_power=o.card_power,
    )


async def _grant_name(session: AsyncSession, kind: str, item_id: str) -> str:
    if kind == "resource" and item_id == "coins":
        return "Pièces"
    model = {"resource": Resource, "booster": Booster, "cosmetic": Cosmetic}.get(kind)
    row = await session.get(model, item_id) if model else None
    return row.name if row else item_id


async def _purchases_in_period(session: AsyncSession, user_id: int, offer: ShopOffer) -> int:
    """Achats déjà faits sur la période de la limite de cette offre."""
    query = select(func.count()).select_from(ShopPurchase).where(
        ShopPurchase.user_id == user_id, ShopPurchase.offer_id == offer.id,
    )
    start = purchase_limits.window_start(_limit_period(offer))
    if start is not None:
        query = query.where(ShopPurchase.purchased_at >= start)
    return (await session.execute(query)).scalar_one()


def _limit_period(offer: ShopOffer) -> str:
    """Période effective : les anciennes offres n'ont qu'une limite par jour."""
    if offer.limit_period != purchase_limits.PERIOD_NONE:
        return offer.limit_period
    return purchase_limits.PERIOD_DAY if offer.purchase_limit_per_day else purchase_limits.PERIOD_NONE


def _limit_count(offer: ShopOffer) -> int:
    if offer.limit_period != purchase_limits.PERIOD_NONE:
        return offer.limit_count
    return offer.purchase_limit_per_day or 0


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
    premium_access = await premium_svc.has_access(session, user)
    out = []
    for o in offers:
        # Offres payées en monnaie premium : réservées à la boutique premium (fermée sauf testeurs).
        if o.resource_id == premium_svc.PREMIUM_RESOURCE_ID and not premium_access:
            continue
        limited = _limit_period(o) != purchase_limits.PERIOD_NONE
        purchases = await _purchases_in_period(session, user.id, o) if limited else 0
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
    """Achète une offre du shop contre la ressource requise, éventuellement par plusieurs."""
    offer = await session.get(ShopOffer, request.offer_id)
    if not offer or not offer.active:
        raise HTTPException(status_code=404, detail="Offre introuvable ou inactive.")

    if offer.resource_id != premium_svc.PREMIUM_RESOURCE_ID:
        await unlocks.require(session, user, "resource_shop")
    if offer.kind == "reroll":
        await unlocks.require(session, user, "rerolls")

    quantity = request.quantity
    if quantity > 1 and not (
        offer.kind in ("booster", "specific_card", "bundle") or (offer.kind == "reroll" and request.to_inventory)
    ):
        raise HTTPException(status_code=400, detail="Cette offre ne s'achète qu'à l'unité.")

    if offer.resource_id == premium_svc.PREMIUM_RESOURCE_ID:
        await premium_svc.require_access(session, user)

    period = _limit_period(offer)
    if period != purchase_limits.PERIOD_NONE:
        allowed = _limit_count(offer)
        done = await _purchases_in_period(session, user.id, offer)
        if done + quantity > allowed:
            left = max(0, allowed - done)
            when = purchase_limits.label(period)
            raise HTTPException(
                status_code=400,
                detail=f"Limite atteinte pour « {offer.name} » ({done}/{allowed} {when}, "
                       f"encore {left} possible(s)).",
            )

    total_price = offer.price * quantity
    await require_balance(session, user, offer.resource_id, total_price)

    cards_out: list = []
    packs_out: list = []
    previous_card = None
    suffix = f" ×{quantity}" if quantity > 1 else ""
    message = f"« {offer.name} »{suffix} acheté !"

    if offer.kind == "booster" and request.to_inventory:
        booster = await session.get(Booster, offer.booster_id) if offer.booster_id else None
        if not booster or not booster.active:
            raise HTTPException(status_code=500, detail="Booster de l'offre introuvable ou retiré.")
        await booster_inventory.grant_bonus(
            session, user.id, booster.id,
            offer.force_min_rarity_id, offer.rarity_weight_multiplier, offer.name, quantity,
        )
        message = f"« {offer.name} »{suffix} ajouté à ton inventaire."

    elif offer.kind == "booster":
        booster = await session.get(Booster, offer.booster_id) if offer.booster_id else None
        if not booster or not booster.active:
            raise HTTPException(status_code=500, detail="Booster de l'offre introuvable ou retiré.")
        packs, new_cards = await pack_service.generate_and_persist_packs(
            session, user.id, booster, quantity=quantity,
            force_min_rarity_id=offer.force_min_rarity_id,
            rarity_weight_multiplier=offer.rarity_weight_multiplier,
        )
        user.packs_opened += quantity
        user.total_cards += new_cards
        packs_out = packs
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
        for _ in range(quantity):
            card = UserCard(
                user_id=user.id,
                character_id=offer.character_id,
                set_id=link.set_id if link else "",
                rarity_id=offer.rarity_id,
                quality_id=offer.quality_id,
                specialty_id=offer.specialty_id,
                jewelry_id=offer.jewelry_id,
            )
            await assign_bought_card_power(session, card, offer)
            session.add(card)
            await session.flush()
            cards_out.append(await build_card_response(session, card))
        user.total_cards += quantity

    elif offer.kind == "reroll" and request.to_inventory:
        if not (offer.reroll_rarity or offer.reroll_quality or offer.reroll_specialty
                or offer.reroll_jewelry or offer.reroll_power):
            raise HTTPException(status_code=500, detail="Offre de reroll mal configurée (aucun axe).")
        await reroll_inventory.grant(session, user.id, offer, quantity)
        message = f"« {offer.name} »{suffix} ajouté à ton inventaire."

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
        await expeditions.ensure_not_on_expedition(session, [card.id])
        previous_card = await build_card_response(session, card)
        await apply_reroll(session, card, offer)
        await activity.track_reroll(session, user, previous_card.rarity_id, card)
        cards_out = [await build_card_response(session, card)]

    elif offer.kind == "bundle":
        if not offer.grants:
            raise HTTPException(status_code=500, detail="Lot vide (aucun contenu configuré).")
        for _ in range(quantity):
            await premium_svc.apply_grants(session, user, offer.grants)

    elif offer.kind == "cosmetic":
        cosmetic = await session.get(Cosmetic, offer.cosmetic_id) if offer.cosmetic_id else None
        if not cosmetic:
            raise HTTPException(status_code=500, detail="Cosmétique de l'offre introuvable.")
        if not await premium_svc.grant_cosmetic(session, user.id, cosmetic.id):
            raise HTTPException(status_code=409, detail="Tu possèdes déjà ce cosmétique.")
        message = f"« {cosmetic.name} » débloqué !"

    else:
        raise HTTPException(status_code=500, detail=f"Type d'offre inconnu: {offer.kind}")

    new_balance = await apply_delta(session, user, offer.resource_id, -total_price)
    for _ in range(quantity):
        session.add(ShopPurchase(user_id=user.id, offer_id=offer.id))
    await quest_progress.increment(session, user.id, "shop_purchases", quantity)
    await refresh_all_best_ranks(session)

    await session.commit()

    return ShopBuyResponse(
        message=message,
        resource_id=offer.resource_id,
        new_balance=new_balance,
        cards=cards_out,
        packs=packs_out,
        previous_card=previous_card,
    )


@router.get("/rerolls", response_model=list[RerollTokenOut])
async def list_reroll_tokens(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Rerolls achetés et gardés en inventaire."""
    return await reroll_inventory.list_owned(session, user.id)


@router.post(
    "/rerolls/{token_id}/use",
    response_model=RerollUseResponse,
    dependencies=[Depends(rate_limit(30, 60))],
)
async def use_reroll_token(
    token_id: int,
    request: RerollUseRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Utilise un reroll de l'inventaire sur une carte possédée."""
    await unlocks.require(session, user, "rerolls")
    return await reroll_inventory.use(session, user, token_id, request.card_id)
