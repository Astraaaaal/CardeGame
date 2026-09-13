"""
Routes admin — édition de contenu (sets, boosters, personnages, types).
Toutes protégées par l'en-tête X-Admin-Key.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, delete, update

from app.database import get_session
from app.core.dependencies import require_admin
from app.models.reference import Set, Rarity, Quality, Specialty, Jewelry
from app.models.booster import Booster, BoosterSet
from app.models.character import Character, CharacterSet, CharacterType
from app.models.card import UserCard
from app.models.economy import Resource, UserResource, ShopOffer, ShopPurchase, DailyFeature
from app.schemas.content import (
    SetIn, SetPatch, SetOut,
    BoosterIn, BoosterPatch, BoosterOut,
    CharacterIn, CharacterPatch, CharacterOut, CharacterSetLink,
    TypeIn, TypePatch, TypeOut,
)
from app.schemas.economy import ResourceIn, ResourcePatch, ShopOfferIn, DailyFeatureIn, DailyFeatureOut

router = APIRouter(dependencies=[Depends(require_admin)])


# ─────────────────────────────  SETS  ─────────────────────────────

@router.get("/sets", response_model=list[SetOut])
async def list_sets(session: AsyncSession = Depends(get_session)):
    sets = (await session.execute(select(Set))).scalars().all()
    b_counts = dict(
        (await session.execute(
            select(BoosterSet.set_id, func.count(func.distinct(BoosterSet.booster_id)))
            .group_by(BoosterSet.set_id)
        )).all()
    )
    c_counts = dict(
        (await session.execute(
            select(CharacterSet.set_id, func.count()).group_by(CharacterSet.set_id)
        )).all()
    )
    return [
        SetOut(
            id=s.id, name=s.name, description=s.description,
            booster_count=b_counts.get(s.id, 0),
            character_count=c_counts.get(s.id, 0),
        )
        for s in sets
    ]


@router.post("/sets", response_model=SetOut, status_code=201)
async def create_set(body: SetIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Set, body.id):
        raise HTTPException(409, f"Le set '{body.id}' existe déjà.")
    s = Set(id=body.id, name=body.name, description=body.description)
    session.add(s)
    await session.commit()
    return SetOut(id=s.id, name=s.name, description=s.description)


@router.patch("/sets/{set_id}", response_model=SetOut)
async def update_set(
    set_id: str, body: SetPatch, session: AsyncSession = Depends(get_session)
):
    s = await session.get(Set, set_id)
    if not s:
        raise HTTPException(404, "Set introuvable.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(s, k, v)
    await session.commit()
    return SetOut(id=s.id, name=s.name, description=s.description)


@router.delete("/sets/{set_id}", status_code=204)
async def delete_set(set_id: str, session: AsyncSession = Depends(get_session)):
    s = await session.get(Set, set_id)
    if not s:
        raise HTTPException(404, "Set introuvable.")
    used_b = (await session.execute(
        select(func.count(func.distinct(BoosterSet.booster_id)))
        .where(BoosterSet.set_id == set_id)
    )).scalar_one()
    used_c = (await session.execute(
        select(func.count()).select_from(CharacterSet).where(CharacterSet.set_id == set_id)
    )).scalar_one()
    if used_b or used_c:
        raise HTTPException(
            409,
            f"Set utilisé par {used_b} booster(s) et {used_c} personnage(s). "
            "Détache-les d'abord.",
        )
    used_cards = (await session.execute(
        select(func.count()).select_from(UserCard).where(UserCard.set_id == set_id)
    )).scalar_one()
    if used_cards:
        raise HTTPException(
            409,
            f"{used_cards} carte(s) déjà possédée(s) par des joueurs référencent ce set. "
            "Suppression impossible (l'historique des joueurs ne doit pas casser).",
        )
    await session.delete(s)
    await session.commit()


# ───────────────────────────  BOOSTERS  ───────────────────────────

async def _booster_out(session: AsyncSession, b: Booster) -> BoosterOut:
    set_ids = (await session.execute(
        select(BoosterSet.set_id).where(BoosterSet.booster_id == b.id)
    )).scalars().all()
    resource = await session.get(Resource, b.resource_id)
    return BoosterOut(
        id=b.id, name=b.name, set_ids=list(set_ids) or [b.set_id],
        cards_count=b.cards_count,
        resource_id=b.resource_id, resource_name=resource.name if resource else b.resource_id,
        price=b.price,
        guaranteed_rare=b.guaranteed_rare, description=b.description,
        active=b.active, visible_in_shop=b.visible_in_shop,
    )


async def _check_sets_exist(session: AsyncSession, set_ids: list[str]) -> None:
    for sid in set_ids:
        if not await session.get(Set, sid):
            raise HTTPException(400, f"Le set '{sid}' n'existe pas.")


async def _replace_booster_sets(session: AsyncSession, booster_id: str, set_ids: list[str]) -> None:
    await session.execute(delete(BoosterSet).where(BoosterSet.booster_id == booster_id))
    for sid in dict.fromkeys(set_ids):  # dédoublonne en gardant l'ordre
        session.add(BoosterSet(booster_id=booster_id, set_id=sid))


@router.get("/boosters", response_model=list[BoosterOut])
async def list_boosters_admin(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Booster))).scalars().all()
    return [await _booster_out(session, b) for b in rows]


@router.post("/boosters", response_model=BoosterOut, status_code=201)
async def create_booster(body: BoosterIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Booster, body.id):
        raise HTTPException(409, f"Le booster '{body.id}' existe déjà.")
    await _check_sets_exist(session, body.set_ids)
    if not await session.get(Resource, body.resource_id):
        raise HTTPException(400, f"La ressource '{body.resource_id}' n'existe pas.")
    b = Booster(
        id=body.id, name=body.name, set_id=body.set_ids[0],
        cards_count=body.cards_count, resource_id=body.resource_id, price=body.price,
        guaranteed_rare=body.guaranteed_rare, description=body.description,
        active=body.active, visible_in_shop=body.visible_in_shop,
    )
    session.add(b)
    await _replace_booster_sets(session, body.id, body.set_ids)
    await session.commit()
    return await _booster_out(session, b)


@router.patch("/boosters/{booster_id}", response_model=BoosterOut)
async def update_booster(
    booster_id: str, body: BoosterPatch, session: AsyncSession = Depends(get_session)
):
    b = await session.get(Booster, booster_id)
    if not b:
        raise HTTPException(404, "Booster introuvable.")
    data = body.model_dump(exclude_unset=True)
    set_ids = data.pop("set_ids", None)
    if data.get("resource_id") and not await session.get(Resource, data["resource_id"]):
        raise HTTPException(400, f"La ressource '{data['resource_id']}' n'existe pas.")
    for k, v in data.items():
        setattr(b, k, v)
    if set_ids is not None:
        await _check_sets_exist(session, set_ids)
        b.set_id = set_ids[0]
        await _replace_booster_sets(session, booster_id, set_ids)
    await session.commit()
    return await _booster_out(session, b)


@router.delete("/boosters/{booster_id}", status_code=204)
async def delete_booster(
    booster_id: str, session: AsyncSession = Depends(get_session)
):
    b = await session.get(Booster, booster_id)
    if not b:
        raise HTTPException(404, "Booster introuvable.")
    await session.execute(delete(BoosterSet).where(BoosterSet.booster_id == booster_id))
    await session.delete(b)
    await session.commit()


# ──────────────────────────  PERSONNAGES  ─────────────────────────

async def _char_out(session: AsyncSession, c: Character) -> CharacterOut:
    links = (await session.execute(
        select(CharacterSet).where(CharacterSet.character_id == c.id)
    )).scalars().all()
    return CharacterOut(
        id=c.id, name=c.name, description=c.description, type=c.type,
        gen=c.gen, image_url=c.image_url,
        sets=[CharacterSetLink(set_id=l.set_id, weight=l.weight) for l in links],
    )


async def _set_links(session: AsyncSession, char_id: str, links: list[CharacterSetLink]):
    seen = set()
    for link in links:
        if link.set_id in seen:
            continue
        seen.add(link.set_id)
        if not await session.get(Set, link.set_id):
            raise HTTPException(400, f"Le set '{link.set_id}' n'existe pas.")
        session.add(CharacterSet(
            character_id=char_id, set_id=link.set_id, weight=link.weight
        ))


@router.get("/characters", response_model=list[CharacterOut])
async def list_characters(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Character))).scalars().all()
    return [await _char_out(session, c) for c in rows]


@router.post("/characters", response_model=CharacterOut, status_code=201)
async def create_character(
    body: CharacterIn, session: AsyncSession = Depends(get_session)
):
    if await session.get(Character, body.id):
        raise HTTPException(409, f"Le personnage '{body.id}' existe déjà.")
    c = Character(
        id=body.id, name=body.name, description=body.description,
        type=body.type, gen=body.gen, image_url=body.image_url,
    )
    session.add(c)
    await _set_links(session, body.id, body.sets)
    await session.commit()
    return await _char_out(session, c)


@router.patch("/characters/{char_id}", response_model=CharacterOut)
async def update_character(
    char_id: str, body: CharacterPatch, session: AsyncSession = Depends(get_session)
):
    c = await session.get(Character, char_id)
    if not c:
        raise HTTPException(404, "Personnage introuvable.")
    data = body.model_dump(exclude_unset=True)
    new_links = data.pop("sets", None)
    for k, v in data.items():
        setattr(c, k, v)
    if new_links is not None:
        await session.execute(
            delete(CharacterSet).where(CharacterSet.character_id == char_id)
        )
        await _set_links(session, char_id, [CharacterSetLink(**l) for l in new_links])
    await session.commit()
    return await _char_out(session, c)


@router.delete("/characters/{char_id}", status_code=204)
async def delete_character(
    char_id: str, session: AsyncSession = Depends(get_session)
):
    c = await session.get(Character, char_id)
    if not c:
        raise HTTPException(404, "Personnage introuvable.")
    used_cards = (await session.execute(
        select(func.count()).select_from(UserCard).where(UserCard.character_id == char_id)
    )).scalar_one()
    if used_cards:
        raise HTTPException(
            409,
            f"{used_cards} carte(s) déjà possédée(s) par des joueurs référencent ce "
            "personnage. Suppression impossible (l'historique des joueurs ne doit pas casser).",
        )
    await session.execute(
        delete(CharacterSet).where(CharacterSet.character_id == char_id)
    )
    await session.delete(c)
    await session.commit()


# ──────────────────────────────  TYPES  ───────────────────────────

@router.get("/types", response_model=list[TypeOut])
async def list_types(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(CharacterType).order_by(CharacterType.name))).scalars().all()
    counts = dict(
        (await session.execute(
            select(Character.type, func.count()).group_by(Character.type)
        )).all()
    )
    return [
        TypeOut(id=t.id, name=t.name, color=t.color, in_use=counts.get(t.name, 0))
        for t in rows
    ]


@router.post("/types", response_model=TypeOut, status_code=201)
async def create_type(body: TypeIn, session: AsyncSession = Depends(get_session)):
    if await session.get(CharacterType, body.id):
        raise HTTPException(409, f"Le type '{body.id}' existe déjà.")
    existing_names = (await session.execute(
        select(CharacterType).where(CharacterType.name == body.name)
    )).scalar_one_or_none()
    if existing_names:
        raise HTTPException(409, f"Le nom de type '{body.name}' existe déjà.")
    t = CharacterType(
        id=body.id, name=body.name,
        color_r=body.color_r, color_g=body.color_g, color_b=body.color_b,
    )
    session.add(t)
    await session.commit()
    return TypeOut(id=t.id, name=t.name, color=t.color, in_use=0)


@router.patch("/types/{type_id}", response_model=TypeOut)
async def update_type(type_id: str, body: TypePatch, session: AsyncSession = Depends(get_session)):
    t = await session.get(CharacterType, type_id)
    if not t:
        raise HTTPException(404, "Type introuvable.")
    data = body.model_dump(exclude_unset=True)

    new_name = data.get("name")
    if new_name and new_name != t.name:
        clash = (await session.execute(
            select(CharacterType).where(CharacterType.name == new_name, CharacterType.id != type_id)
        )).scalar_one_or_none()
        if clash:
            raise HTTPException(409, f"Le nom de type '{new_name}' existe déjà.")
        # Les personnages référencent le type par son NOM (pas son id) : on
        # doit répercuter le renommage pour ne pas les orphelin-iser.
        await session.execute(
            update(Character).where(Character.type == t.name).values(type=new_name)
        )

    for k, v in data.items():
        setattr(t, k, v)
    await session.commit()

    used = (await session.execute(
        select(func.count()).select_from(Character).where(Character.type == t.name)
    )).scalar_one()
    return TypeOut(id=t.id, name=t.name, color=t.color, in_use=used)


@router.delete("/types/{type_id}", status_code=204)
async def delete_type(type_id: str, session: AsyncSession = Depends(get_session)):
    t = await session.get(CharacterType, type_id)
    if not t:
        raise HTTPException(404, "Type introuvable.")
    used = (await session.execute(
        select(func.count()).select_from(Character).where(Character.type == t.name)
    )).scalar_one()
    if used:
        raise HTTPException(
            409, f"Type utilisé par {used} personnage(s). Change leur type d'abord."
        )
    await session.delete(t)
    await session.commit()


# ─────────────────────────────  RESSOURCES  ───────────────────────

@router.get("/resources")
async def list_resources(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Resource).order_by(Resource.name))).scalars().all()
    return [
        {"id": r.id, "name": r.name, "description": r.description, "protected": r.protected}
        for r in rows
    ]


@router.post("/resources", status_code=201)
async def create_resource(body: ResourceIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Resource, body.id):
        raise HTTPException(409, f"La ressource '{body.id}' existe déjà.")
    r = Resource(id=body.id, name=body.name, description=body.description)
    session.add(r)
    await session.commit()
    return {"id": r.id, "name": r.name, "description": r.description, "protected": r.protected}


@router.patch("/resources/{resource_id}")
async def update_resource(resource_id: str, body: ResourcePatch, session: AsyncSession = Depends(get_session)):
    r = await session.get(Resource, resource_id)
    if not r:
        raise HTTPException(404, "Ressource introuvable.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(r, k, v)
    await session.commit()
    return {"id": r.id, "name": r.name, "description": r.description, "protected": r.protected}


@router.delete("/resources/{resource_id}", status_code=204)
async def delete_resource(resource_id: str, session: AsyncSession = Depends(get_session)):
    r = await session.get(Resource, resource_id)
    if not r:
        raise HTTPException(404, "Ressource introuvable.")
    if r.protected:
        raise HTTPException(409, "Cette ressource est protégée et ne peut pas être supprimée.")
    used_offers = (await session.execute(
        select(func.count()).select_from(ShopOffer).where(ShopOffer.resource_id == resource_id)
    )).scalar_one()
    used_boosters = (await session.execute(
        select(func.count()).select_from(Booster).where(Booster.resource_id == resource_id)
    )).scalar_one()
    held = (await session.execute(
        select(func.count()).select_from(UserResource)
        .where(UserResource.resource_id == resource_id, UserResource.amount > 0)
    )).scalar_one()
    if used_offers or used_boosters or held:
        raise HTTPException(
            409,
            f"Ressource utilisée par {used_offers} offre(s), {used_boosters} booster(s) "
            f"et détenue par {held} joueur(s). Suppression impossible.",
        )
    await session.delete(r)
    await session.commit()


# ─────────────────────────────  SHOP OFFERS  ──────────────────────

@router.get("/shop-offers")
async def list_shop_offers(session: AsyncSession = Depends(get_session)):
    from app.api.shop import _offer_response
    from app.services.daily_feature import get_todays_featured_offer_id
    rows = (await session.execute(select(ShopOffer))).scalars().all()
    featured_id = await get_todays_featured_offer_id(session)
    return [await _offer_response(session, o, featured_id) for o in rows]


@router.post("/shop-offers", status_code=201)
async def create_shop_offer(body: ShopOfferIn, session: AsyncSession = Depends(get_session)):
    from app.api.shop import _offer_response
    if await session.get(ShopOffer, body.id):
        raise HTTPException(409, f"L'offre '{body.id}' existe déjà.")
    if not await session.get(Resource, body.resource_id):
        raise HTTPException(400, f"La ressource '{body.resource_id}' n'existe pas.")

    if body.kind == "booster" and not body.booster_id:
        raise HTTPException(400, "Un booster est requis pour une offre de type 'booster'.")
    if body.kind == "specific_card" and not all(
        [body.character_id, body.rarity_id, body.quality_id, body.specialty_id, body.jewelry_id]
    ):
        raise HTTPException(
            400, "Personnage, rareté, qualité, spécialité et jewelry sont requis "
                 "pour une offre de type 'specific_card'.",
        )
    if body.kind == "reroll":
        if not any([body.reroll_rarity, body.reroll_quality, body.reroll_specialty, body.reroll_jewelry]):
            raise HTTPException(400, "Choisis au moins un axe à retirer pour une offre de type 'reroll'.")
        if not body.reroll_mode:
            raise HTTPException(400, "Choisis un mode de reroll (aléatoire ou garanti égal/mieux).")
    if body.booster_id and not await session.get(Booster, body.booster_id):
        raise HTTPException(400, f"Le booster '{body.booster_id}' n'existe pas.")
    if body.force_min_rarity_id and not await session.get(Rarity, body.force_min_rarity_id):
        raise HTTPException(400, f"La rareté '{body.force_min_rarity_id}' n'existe pas.")

    o = ShopOffer(**body.model_dump())
    session.add(o)
    await session.commit()
    return await _offer_response(session, o)


@router.patch("/shop-offers/{offer_id}")
async def update_shop_offer(
    offer_id: str, active: bool, session: AsyncSession = Depends(get_session)
):
    """Active/désactive une offre (retrait rapide du shop sans la supprimer)."""
    from app.api.shop import _offer_response
    o = await session.get(ShopOffer, offer_id)
    if not o:
        raise HTTPException(404, "Offre introuvable.")
    o.active = active
    await session.commit()
    return await _offer_response(session, o)


@router.delete("/shop-offers/{offer_id}", status_code=204)
async def delete_shop_offer(offer_id: str, session: AsyncSession = Depends(get_session)):
    o = await session.get(ShopOffer, offer_id)
    if not o:
        raise HTTPException(404, "Offre introuvable.")
    # Journal d'achats et épingles "booster du jour" : simples métadonnées,
    # pas des biens de joueur — on les efface sans bloquer la suppression.
    await session.execute(delete(ShopPurchase).where(ShopPurchase.offer_id == offer_id))
    await session.execute(delete(DailyFeature).where(DailyFeature.offer_id == offer_id))
    await session.delete(o)
    await session.commit()


# ───────────────────────  BOOSTER DU JOUR (épingle)  ──────────────

@router.get("/daily-feature", response_model=DailyFeatureOut | None)
async def get_daily_feature(target_date: str | None = None, session: AsyncSession = Depends(get_session)):
    """Épingle active pour `target_date` (défaut : aujourd'hui), s'il y en a une."""
    from datetime import date as _date
    d = _date.fromisoformat(target_date) if target_date else _date.today()
    pinned = await session.get(DailyFeature, d)
    if not pinned:
        return None
    offer = await session.get(ShopOffer, pinned.offer_id)
    return DailyFeatureOut(
        feature_date=pinned.feature_date, offer_id=pinned.offer_id,
        offer_name=offer.name if offer else pinned.offer_id,
    )


@router.post("/daily-feature", response_model=DailyFeatureOut)
async def set_daily_feature(body: DailyFeatureIn, session: AsyncSession = Depends(get_session)):
    """Épingle une offre pour une date donnée (défaut : aujourd'hui) — surclasse la rotation auto."""
    from datetime import date as _date
    offer = await session.get(ShopOffer, body.offer_id)
    if not offer:
        raise HTTPException(400, f"L'offre '{body.offer_id}' n'existe pas.")
    d = body.feature_date or _date.today()
    existing = await session.get(DailyFeature, d)
    if existing:
        existing.offer_id = body.offer_id
    else:
        session.add(DailyFeature(feature_date=d, offer_id=body.offer_id))
    await session.commit()
    return DailyFeatureOut(feature_date=d, offer_id=offer.id, offer_name=offer.name)


@router.delete("/daily-feature/{target_date}", status_code=204)
async def clear_daily_feature(target_date: str, session: AsyncSession = Depends(get_session)):
    """Retire l'épingle d'une date (retour à la rotation automatique)."""
    from datetime import date as _date
    d = _date.fromisoformat(target_date)
    pinned = await session.get(DailyFeature, d)
    if pinned:
        await session.delete(pinned)
        await session.commit()


# ──────────────  TABLES DE RÉGLAGE (lecture seule ici)  ───────────

@router.get("/tuning")
async def tuning(session: AsyncSession = Depends(get_session)):
    """raretés / qualités / spécialités / jewelries + leurs poids (pour info)."""
    async def dump(model):
        rows = (await session.execute(select(model))).scalars().all()
        return [
            {
                "id": r.id, "name": r.name, "weight": getattr(r, "weight", None),
                "recycle_value": getattr(r, "recycle_value", None),
            }
            for r in rows
        ]
    return {
        "rarities": await dump(Rarity),
        "qualities": await dump(Quality),
        "specialties": await dump(Specialty),
        "jewelries": await dump(Jewelry),
    }
