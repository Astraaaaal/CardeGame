"""
Route publique — types de personnage (nom + couleur). Pas d'auth : donnée
cosmétique nécessaire au rendu des cartes pour n'importe quel client (jeu ET
panneau admin), pas de raison de la protéger.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.character import CharacterType
from app.schemas.content import TypeOut

router = APIRouter()


@router.get("/", response_model=list[TypeOut])
async def list_types(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(CharacterType))).scalars().all()
    return [TypeOut(id=t.id, name=t.name, color=t.color) for t in rows]
