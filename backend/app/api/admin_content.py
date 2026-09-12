"""
Routes admin — édition de contenu (sets, boosters, personnages, types).
Toutes protégées par l'en-tête X-Admin-Key.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, delete

from app.database import get_session
from app.core.dependencies import require_admin
from app.models.reference import Set, Rarity, Quality, Specialty, Jewelry
from app.models.booster import Booster, BoosterSet
from app.models.character import Character, CharacterSet, CharacterType
from app.models.card import UserCard
from app.schemas.content import (
    SetIn, SetPatch, SetOut,
    BoosterIn, BoosterPatch, BoosterOut,
    CharacterIn, CharacterPatch, CharacterOut, CharacterSetLink,
    TypeIn, TypeOut,
)

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
    return BoosterOut(
        id=b.id, name=b.name, set_ids=list(set_ids) or [b.set_id],
        cards_count=b.cards_count, price=b.price,
        guaranteed_rare=b.guaranteed_rare, description=b.description,
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
    b = Booster(
        id=body.id, name=body.name, set_id=body.set_ids[0],
        cards_count=body.cards_count, price=body.price,
        guaranteed_rare=body.guaranteed_rare, description=body.description,
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
    rows = (await session.execute(select(CharacterType))).scalars().all()
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


# ──────────────  TABLES DE RÉGLAGE (lecture seule ici)  ───────────

@router.get("/tuning")
async def tuning(session: AsyncSession = Depends(get_session)):
    """raretés / qualités / spécialités / jewelries + leurs poids (pour info)."""
    async def dump(model):
        rows = (await session.execute(select(model))).scalars().all()
        return [
            {"id": r.id, "name": r.name, "weight": getattr(r, "weight", None)}
            for r in rows
        ]
    return {
        "rarities": await dump(Rarity),
        "qualities": await dump(Quality),
        "specialties": await dump(Specialty),
        "jewelries": await dump(Jewelry),
    }
