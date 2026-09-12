"""
Routes collection — Inventaire du joueur (groupé, filtré, trié).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, col
from typing import Optional

from app.database import get_session
from app.core.dependencies import get_current_user
from app.core.ratelimit import rate_limit
from app.models.user import User
from app.models.card import UserCard
from app.models.character import Character
from app.models.booster import Booster
from app.models.reference import Set, Rarity, Quality, Specialty, Jewelry
from app.models.economy import Resource, UserResource
from app.schemas.card import CardResponse, CardGroupResponse
from app.schemas.collection import CollectionResponse
from app.schemas.economy import RecycleRequest, RecycleResponse
from app.services.card_view import build_card_response

router = APIRouter()

RECYCLE_RESOURCE_ID = "dust"  # seule source de recyclage pour l'instant

# Ordres de tri (identiques à collection.py Pygame)
RARITY_ORDER = {"legendary": 4, "epic": 3, "rare": 2, "common": 1}
QUALITY_ORDER = {
    "authentic": 14, "mint": 13, "graded": 12, "excellent": 11,
    "preserved": 10, "fair": 9, "worn": 8, "faded": 7,
    "scratched": 6, "torn": 5, "damaged": 4,
    "unplayable": 3, "unreadable": 2, "destroyed": 1,
}
SPECIALTY_ORDER = {"shiny": 4, "ex": 3, "full_art": 2, "normal": 1}
JEWELRY_ORDER = {"prismatic": 5, "diamond": 4, "gold": 3, "silver": 2, "none": 1}


@router.get("/", response_model=CollectionResponse)
async def get_collection(
    sort_by: str = Query("rarity", pattern="^(rarity|name|quality|specialty|jewelry|probability)$"),
    set_id: Optional[str] = Query(None),
    rarity_id: Optional[str] = Query(None),
    specialty_id: Optional[str] = Query(None),
    jewelry_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retourne la collection du joueur, groupée par combinaison unique.
    Supporte le tri et les filtres.
    """
    # Requête de base
    query = select(UserCard).where(UserCard.user_id == user.id)

    # Filtres
    if set_id:
        query = query.where(UserCard.set_id == set_id)
    if rarity_id:
        query = query.where(UserCard.rarity_id == rarity_id)
    if specialty_id:
        query = query.where(UserCard.specialty_id == specialty_id)
    if jewelry_id:
        query = query.where(UserCard.jewelry_id == jewelry_id)

    result = await session.execute(query)
    all_cards = result.scalars().all()

    if not all_cards:
        return CollectionResponse(total_cards=0, unique_cards=0, groups=[])

    # Charger les tables de référence
    chars_map = await _load_map(session, Character)
    sets_map = await _load_map(session, Set)
    rarities_map = await _load_map(session, Rarity)
    qualities_map = await _load_map(session, Quality)
    specialties_map = await _load_map(session, Specialty)
    jewelries_map = await _load_map(session, Jewelry)
    boosters_map = await _load_map(session, Booster)

    # Regrouper (même logique que _card_group_key)
    groups: dict[tuple, dict] = {}
    for card in all_cards:
        key = (card.character_id, card.rarity_id, card.quality_id,
               card.specialty_id, card.jewelry_id)
        if key not in groups:
            char = chars_map.get(card.character_id)
            set_info = sets_map.get(card.set_id)
            rarity = rarities_map.get(card.rarity_id)
            quality = qualities_map.get(card.quality_id)
            specialty = specialties_map.get(card.specialty_id)
            jewelry = jewelries_map.get(card.jewelry_id)

            groups[key] = {
                "card": CardResponse(
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
                    booster_name=(
                        boosters_map[card.booster_id].name
                        if card.booster_id in boosters_map else None
                    ),
                ),
                "quantity": 1,
            }
        else:
            groups[key]["quantity"] += 1

    # Trier
    group_list = list(groups.values())
    if sort_by == "rarity":
        group_list.sort(
            key=lambda g: RARITY_ORDER.get(g["card"].rarity_id, 0),
            reverse=True,
        )
    elif sort_by == "name":
        group_list.sort(key=lambda g: g["card"].character_name)
    elif sort_by == "quality":
        group_list.sort(
            key=lambda g: QUALITY_ORDER.get(g["card"].quality_id, 0),
            reverse=True,
        )
    elif sort_by == "specialty":
        group_list.sort(
            key=lambda g: SPECIALTY_ORDER.get(g["card"].specialty_id, 0),
            reverse=True,
        )
    elif sort_by == "jewelry":
        group_list.sort(
            key=lambda g: JEWELRY_ORDER.get(g["card"].jewelry_id, 0),
            reverse=True,
        )
    elif sort_by == "probability":
        group_list.sort(key=lambda g: g["card"].drop_probability)

    return CollectionResponse(
        total_cards=len(all_cards),
        unique_cards=len(group_list),
        groups=[CardGroupResponse(**g) for g in group_list],
    )


@router.get("/{card_id}", response_model=CardResponse)
async def get_card_detail(
    card_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Retourne les détails d'une carte précise."""
    result = await session.execute(
        select(UserCard).where(
            UserCard.id == card_id,
            UserCard.user_id == user.id,
        )
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Carte introuvable")

    return await build_card_response(session, card)


@router.post(
    "/recycle",
    response_model=RecycleResponse,
    dependencies=[Depends(rate_limit(30, 60))],
)
async def recycle_cards(
    request: RecycleRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Recycle `count` exemplaires d'une combinaison de carte possédée contre de
    la poussière. Valeur = somme des `recycle_value` de rareté/qualité/
    spécialité/jewelry, tunable côté données (cf. app/migrations.py).
    """
    owned = (await session.execute(
        select(UserCard).where(
            UserCard.user_id == user.id,
            UserCard.character_id == request.character_id,
            UserCard.rarity_id == request.rarity_id,
            UserCard.quality_id == request.quality_id,
            UserCard.specialty_id == request.specialty_id,
            UserCard.jewelry_id == request.jewelry_id,
        )
    )).scalars().all()

    if len(owned) < request.count:
        raise HTTPException(
            status_code=400,
            detail=f"Tu ne possèdes que {len(owned)} exemplaire(s) de cette carte.",
        )

    resource = await session.get(Resource, RECYCLE_RESOURCE_ID)
    if not resource:
        raise HTTPException(status_code=500, detail="Ressource de recyclage introuvable.")

    rarity = await session.get(Rarity, request.rarity_id)
    quality = await session.get(Quality, request.quality_id)
    specialty = await session.get(Specialty, request.specialty_id)
    jewelry = await session.get(Jewelry, request.jewelry_id)
    per_card = (
        (rarity.recycle_value if rarity else 0)
        + (quality.recycle_value if quality else 0)
        + (specialty.recycle_value if specialty else 0)
        + (jewelry.recycle_value if jewelry else 0)
    )
    total_gain = per_card * request.count

    for card in owned[: request.count]:
        await session.delete(card)

    user_res = await session.get(UserResource, (user.id, RECYCLE_RESOURCE_ID))
    if not user_res:
        user_res = UserResource(user_id=user.id, resource_id=RECYCLE_RESOURCE_ID, amount=0)
        session.add(user_res)
    user_res.amount += total_gain
    user.total_cards = max(0, user.total_cards - request.count)

    await session.commit()

    return RecycleResponse(
        resource_id=RECYCLE_RESOURCE_ID,
        resource_name=resource.name,
        gained=total_gain,
        new_balance=user_res.amount,
        remaining_quantity=len(owned) - request.count,
    )


async def _load_map(session: AsyncSession, model) -> dict:
    result = await session.execute(select(model))
    items = result.scalars().all()
    return {item.id: item for item in items}
