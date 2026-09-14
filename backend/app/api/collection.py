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
from app.schemas.card import CardResponse, CardGroupResponse, CardPowerBreakdown, CardCopyOut, CardCopiesResponse
from app.schemas.collection import CollectionResponse, ProbabilityItem, ProbabilityTableResponse
from app.schemas.economy import RecycleRequest, RecycleResponse
from app.services.card_view import build_card_response
from app.services.power import combined_rarity
from app.services.tier_order import (
    RARITY_ORDER, QUALITY_ORDER, SPECIALTY_ORDER, JEWELRY_ORDER, rank,
)

router = APIRouter()

RECYCLE_RESOURCE_ID = "dust"  # seule source de recyclage pour l'instant


_OP_PATTERN = "^(eq|gte|lte)$"


def _matches_tier(axis: str, card_value: str, filter_value: Optional[str], op: str) -> bool:
    """
    eq  : valeur exacte.
    gte : ce palier OU AU-DESSUS ("à partir de tel palier").
    lte : ce palier OU EN DESSOUS ("ce palier et en dessous").
    """
    if not filter_value:
        return True
    if op == "eq":
        return card_value == filter_value
    target = rank(axis, filter_value)
    current = rank(axis, card_value)
    return current >= target if op == "gte" else current <= target


@router.get("/probabilities", response_model=ProbabilityTableResponse)
async def get_probabilities(session: AsyncSession = Depends(get_session)):
    """
    Table publique des probabilités de base par axe (rareté/qualité/spécialité/
    jewelry), telles qu'utilisées par le tirage normal d'un pack — cf.
    CardGeneratorService._generate_single. Un booster "rare garantie" ou une
    offre spéciale du shop peuvent temporairement relever la rareté du tirage ;
    ce tableau montre les poids de base, pas ces overrides ponctuels.
    """
    async def _table(model, axis: str) -> list[ProbabilityItem]:
        rows = (await session.execute(select(model))).scalars().all()
        total = sum(r.weight for r in rows) or 1.0
        items = [
            ProbabilityItem(id=r.id, name=r.name, weight=r.weight, percentage=round(r.weight / total * 100, 3))
            for r in rows
        ]
        items.sort(key=lambda i: rank(axis, i.id), reverse=True)
        return items

    return ProbabilityTableResponse(
        rarities=await _table(Rarity, "rarity"),
        qualities=await _table(Quality, "quality"),
        specialties=await _table(Specialty, "specialty"),
        jewelries=await _table(Jewelry, "jewelry"),
    )


@router.get("/", response_model=CollectionResponse)
async def get_collection(
    sort_by: str = Query("rarity", pattern="^(rarity|name|quality|specialty|jewelry|probability|obtained_at|power|luck)$"),
    set_id: Optional[str] = Query(None),
    rarity_id: Optional[str] = Query(None),
    rarity_op: str = Query("eq", pattern=_OP_PATTERN),
    quality_id: Optional[str] = Query(None),
    quality_op: str = Query("eq", pattern=_OP_PATTERN),
    specialty_id: Optional[str] = Query(None),
    specialty_op: str = Query("eq", pattern=_OP_PATTERN),
    jewelry_id: Optional[str] = Query(None),
    jewelry_op: str = Query("eq", pattern=_OP_PATTERN),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Retourne la collection du joueur, groupée par combinaison unique.
    Supporte le tri et les filtres — pour rareté/qualité/spécialité/jewelry,
    chaque filtre accepte un mode "eq" (exact), "gte" (ce palier et au-dessus)
    ou "lte" (ce palier et en dessous), basé sur tier_order.rank().
    """
    # Requête de base — seul set_id reste un filtre exact simple côté SQL,
    # les 4 axes à palier sont filtrés en Python (comparaison de rang).
    query = select(UserCard).where(UserCard.user_id == user.id)
    if set_id:
        query = query.where(UserCard.set_id == set_id)

    result = await session.execute(query)
    all_cards = [
        c for c in result.scalars().all()
        if _matches_tier("rarity", c.rarity_id, rarity_id, rarity_op)
        and _matches_tier("quality", c.quality_id, quality_id, quality_op)
        and _matches_tier("specialty", c.specialty_id, specialty_id, specialty_op)
        and _matches_tier("jewelry", c.jewelry_id, jewelry_id, jewelry_op)
    ]

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
                    power=card.power,
                    combined_rarity=combined_rarity(
                        card.power, card.drop_probability, card.rarity_id,
                        card.quality_id, card.specialty_id, card.jewelry_id,
                    ),
                    rendered_url=card.rendered_url,
                    obtained_at=card.obtained_at,
                    booster_id=card.booster_id,
                    booster_name=(
                        boosters_map[card.booster_id].name
                        if card.booster_id in boosters_map else None
                    ),
                    booster_cover_url=(
                        boosters_map[card.booster_id].cover_image_url or None
                        if card.booster_id in boosters_map else None
                    ),
                ),
                "quantity": 1,
            }
        else:
            groups[key]["quantity"] += 1
            # Plusieurs exemplaires de la même combinaison peuvent avoir été
            # obtenus à des moments différents : on retient la date la plus
            # récente pour l'affichage et le tri par date d'obtention.
            if card.obtained_at > groups[key]["card"].obtained_at:
                groups[key]["card"].obtained_at = card.obtained_at
            # Idem pour la puissance : on retient le meilleur tirage parmi les
            # exemplaires possédés de cette combinaison (le détail par
            # exemplaire reste consultable via GET /collection/powers).
            if (card.power or 0) > (groups[key]["card"].power or 0):
                groups[key]["card"].power = card.power
                groups[key]["card"].combined_rarity = combined_rarity(
                    card.power, card.drop_probability, card.rarity_id,
                    card.quality_id, card.specialty_id, card.jewelry_id,
                )

    # Trier — "profond" : le nom sert toujours de départage à rang égal.
    # Tri Python stable => on trie d'abord par nom (ordre alphabétique fixe),
    # puis par la clé principale, qui ne fait alors que réordonner les groupes
    # de même rang sans casser leur ordre alphabétique interne.
    group_list = list(groups.values())
    group_list.sort(key=lambda g: g["card"].character_name.lower())
    if sort_by == "rarity":
        group_list.sort(
            key=lambda g: RARITY_ORDER.get(g["card"].rarity_id, 0),
            reverse=True,
        )
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
    elif sort_by == "obtained_at":
        # Plus récent d'abord (dernier exemplaire obtenu par groupe, cf. plus haut).
        group_list.sort(key=lambda g: g["card"].obtained_at, reverse=True)
    elif sort_by == "power":
        # Distinct de "probability" (rareté réelle, exacte et déterministe) :
        # la puissance est un tirage aléatoire propre à chaque exemplaire —
        # deux cartes avec la même combinaison peuvent avoir des puissances différentes.
        group_list.sort(key=lambda g: g["card"].power or 0, reverse=True)
    elif sort_by == "luck":
        # "Chance" : combine la rareté de la combinaison ET la rareté du
        # tirage de puissance en une seule rareté globale ("1 sur X" — cf.
        # combined_rarity). Un tirage 1/1000 à 980 (X ≈ 47 600) ressort
        # devant un tirage 1/1100 à 150 (X ≈ 1 270), et une carte 1/5000 à
        # 80% de son maximum reste devant une commune 1/10 tirée à 100% de
        # son maximum — contrairement à un simple % normalisé qui effacerait
        # le poids de la rareté de base.
        group_list.sort(key=lambda g: g["card"].combined_rarity or 0, reverse=True)

    return CollectionResponse(
        total_cards=len(all_cards),
        unique_cards=len(group_list),
        groups=[CardGroupResponse(**g) for g in group_list],
    )


@router.get("/powers", response_model=CardPowerBreakdown)
async def get_card_powers(
    character_id: str = Query(...),
    rarity_id: str = Query(...),
    quality_id: str = Query(...),
    specialty_id: str = Query(...),
    jewelry_id: str = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Détail de la puissance de chaque exemplaire possédé d'une combinaison —
    la carte groupée n'affiche que la meilleure des deux, ceci permet de
    voir la répartition réelle (au clic, côté collection).
    """
    rows = (await session.execute(
        select(UserCard.power).where(
            UserCard.user_id == user.id,
            UserCard.character_id == character_id,
            UserCard.rarity_id == rarity_id,
            UserCard.quality_id == quality_id,
            UserCard.specialty_id == specialty_id,
            UserCard.jewelry_id == jewelry_id,
        )
    )).scalars().all()
    powers = sorted(rows, key=lambda p: (p is None, -(p or 0)))
    return CardPowerBreakdown(powers=powers)


@router.get("/copies", response_model=CardCopiesResponse)
async def get_card_copies(
    character_id: str = Query(...),
    rarity_id: str = Query(...),
    quality_id: str = Query(...),
    specialty_id: str = Query(...),
    jewelry_id: str = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Identifiant + puissance de chaque exemplaire possédé d'une combinaison —
    sert à choisir un exemplaire précis à apporter dans une session d'échange
    (contrairement à /powers qui ne sert qu'à l'affichage, sans id).
    """
    rows = (await session.execute(
        select(UserCard.id, UserCard.power).where(
            UserCard.user_id == user.id,
            UserCard.character_id == character_id,
            UserCard.rarity_id == rarity_id,
            UserCard.quality_id == quality_id,
            UserCard.specialty_id == specialty_id,
            UserCard.jewelry_id == jewelry_id,
        )
    )).all()
    copies = sorted(
        (CardCopyOut(id=r.id, power=r.power) for r in rows),
        key=lambda c: (c.power is None, -(c.power or 0)),
    )
    return CardCopiesResponse(copies=copies)


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
