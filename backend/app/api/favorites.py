"""
Routes — favoris (catégories nommées et colorées) et verrou anti-recyclage,
tous deux posés sur des exemplaires précis.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.dependencies import get_current_user
from app.database import get_session
from app.models.card import UserCard
from app.models.favorite import MAX_CATEGORIES, FavoriteCard, FavoriteCategory
from app.models.user import User

router = APIRouter()


class CategoryBody(BaseModel):
    name: str = Field(min_length=1, max_length=24)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")


class CardsBody(BaseModel):
    card_ids: list[str] = Field(min_length=1, max_length=20_000)


class LockBody(CardsBody):
    locked: bool


async def _owned_ids(session: AsyncSession, user: User, ids: list[str]) -> list[str]:
    ids = list(dict.fromkeys(ids))
    owned = (await session.execute(
        select(UserCard.id).where(UserCard.id.in_(ids), UserCard.user_id == user.id)
    )).scalars().all()
    if len(owned) != len(ids):
        raise HTTPException(404, "Une ou plusieurs cartes sont introuvables.")
    return ids


async def _category(session: AsyncSession, user: User, category_id: int) -> FavoriteCategory:
    cat = await session.get(FavoriteCategory, category_id)
    if not cat or cat.user_id != user.id:
        raise HTTPException(404, "Catégorie introuvable.")
    return cat


async def _list(session: AsyncSession, user: User) -> list[dict]:
    cats = (await session.execute(
        select(FavoriteCategory).where(FavoriteCategory.user_id == user.id).order_by(FavoriteCategory.id)
    )).scalars().all()
    counts = dict((await session.execute(
        select(FavoriteCard.category_id, func.count()).where(FavoriteCard.category_id.in_([c.id for c in cats]))
        .group_by(FavoriteCard.category_id)
    )).all()) if cats else {}
    return [{"id": c.id, "name": c.name, "color": c.color, "count": counts.get(c.id, 0)} for c in cats]


@router.get("")
async def list_categories(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await _list(session, user)


@router.post("")
async def create_category(body: CategoryBody, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    count = (await session.execute(
        select(func.count()).select_from(FavoriteCategory).where(FavoriteCategory.user_id == user.id)
    )).scalar_one()
    if count >= MAX_CATEGORIES:
        raise HTTPException(400, f"{MAX_CATEGORIES} catégories de favoris au maximum.")
    session.add(FavoriteCategory(user_id=user.id, name=body.name.strip(), color=body.color))
    await session.commit()
    return await _list(session, user)


@router.patch("/{category_id}")
async def update_category(category_id: int, body: CategoryBody, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    cat = await _category(session, user, category_id)
    cat.name, cat.color = body.name.strip(), body.color
    session.add(cat)
    await session.commit()
    return await _list(session, user)


@router.delete("/{category_id}")
async def delete_category(category_id: int, user: User = Depends(get_current_user),
                          session: AsyncSession = Depends(get_session)):
    cat = await _category(session, user, category_id)
    await session.execute(delete(FavoriteCard).where(FavoriteCard.category_id == cat.id))
    await session.delete(cat)
    await session.commit()
    return await _list(session, user)


@router.post("/{category_id}/cards")
async def add_cards(category_id: int, body: CardsBody, user: User = Depends(get_current_user),
                    session: AsyncSession = Depends(get_session)):
    cat = await _category(session, user, category_id)
    ids = await _owned_ids(session, user, body.card_ids)
    already = set((await session.execute(
        select(FavoriteCard.user_card_id).where(FavoriteCard.category_id == cat.id, FavoriteCard.user_card_id.in_(ids))
    )).scalars().all())
    session.add_all(FavoriteCard(category_id=cat.id, user_card_id=i) for i in ids if i not in already)
    await session.commit()
    return await _list(session, user)


@router.post("/{category_id}/cards/remove")
async def remove_cards(category_id: int, body: CardsBody, user: User = Depends(get_current_user),
                       session: AsyncSession = Depends(get_session)):
    cat = await _category(session, user, category_id)
    await session.execute(delete(FavoriteCard).where(
        FavoriteCard.category_id == cat.id, FavoriteCard.user_card_id.in_(body.card_ids)))
    await session.commit()
    return await _list(session, user)


@router.post("/lock")
async def lock_cards(body: LockBody, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    """Verrouille / déverrouille des exemplaires : un exemplaire verrouillé ne peut pas être recyclé."""
    ids = await _owned_ids(session, user, body.card_ids)
    await session.execute(update(UserCard).where(UserCard.id.in_(ids)).values(locked=body.locked))
    await session.commit()
    return {"ok": True}
