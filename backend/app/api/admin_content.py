"""
Routes admin — édition de contenu (sets, boosters, personnages).
Toutes protégées par l'en-tête X-Admin-Key.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func, delete

from app.database import get_session
from app.core.dependencies import require_admin
from app.models.reference import Set, Rarity, Quality, Specialty, Jewelry
from app.models.booster import Booster
from app.models.character import Character, CharacterSet
from app.schemas.content import (
    SetIn, SetPatch, SetOut,
    BoosterIn, BoosterPatch, BoosterOut,
    CharacterIn, CharacterPatch, CharacterOut, CharacterSetLink,
)

router = APIRouter(dependencies=[Depends(require_admin)])


# ─────────────────────────────  SETS  ─────────────────────────────

@router.get("/sets", response_model=list[SetOut])
async def list_sets(session: AsyncSession = Depends(get_session)):
    sets = (await session.execute(select(Set))).scalars().all()
    b_counts = dict(
        (await session.execute(
            select(Booster.set_id, func.count()).group_by(Booster.set_id)
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
        select(func.count()).select_from(Booster).where(Booster.set_id == set_id)
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
    await session.delete(s)
    await session.commit()


# ───────────────────────────  BOOSTERS  ───────────────────────────

def _booster_out(b: Booster) -> BoosterOut:
    return BoosterOut(
        id=b.id, name=b.name, set_id=b.set_id, cards_count=b.cards_count,
        price=b.price, guaranteed_rare=b.guaranteed_rare, description=b.description,
    )


@router.get("/boosters", response_model=list[BoosterOut])
async def list_boosters_admin(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(Booster))).scalars().all()
    return [_booster_out(b) for b in rows]


@router.post("/boosters", response_model=BoosterOut, status_code=201)
async def create_booster(body: BoosterIn, session: AsyncSession = Depends(get_session)):
    if await session.get(Booster, body.id):
        raise HTTPException(409, f"Le booster '{body.id}' existe déjà.")
    if not await session.get(Set, body.set_id):
        raise HTTPException(400, f"Le set '{body.set_id}' n'existe pas.")
    b = Booster(**body.model_dump())
    session.add(b)
    await session.commit()
    return _booster_out(b)


@router.patch("/boosters/{booster_id}", response_model=BoosterOut)
async def update_booster(
    booster_id: str, body: BoosterPatch, session: AsyncSession = Depends(get_session)
):
    b = await session.get(Booster, booster_id)
    if not b:
        raise HTTPException(404, "Booster introuvable.")
    data = body.model_dump(exclude_unset=True)
    if "set_id" in data and not await session.get(Set, data["set_id"]):
        raise HTTPException(400, f"Le set '{data['set_id']}' n'existe pas.")
    for k, v in data.items():
        setattr(b, k, v)
    await session.commit()
    return _booster_out(b)


@router.delete("/boosters/{booster_id}", status_code=204)
async def delete_booster(
    booster_id: str, session: AsyncSession = Depends(get_session)
):
    b = await session.get(Booster, booster_id)
    if not b:
        raise HTTPException(404, "Booster introuvable.")
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
    await session.execute(
        delete(CharacterSet).where(CharacterSet.character_id == char_id)
    )
    await session.delete(c)
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
