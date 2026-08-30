"""
Routes admin — Seed des données, utilitaires.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import require_admin
from app.schemas.auth import MessageResponse

# Toutes les routes de ce routeur exigent l'en-tête X-Admin-Key.
router = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/seed", response_model=MessageResponse)
async def seed_database(
    session: AsyncSession = Depends(get_session),
):
    """
    Seed les données de référence (sets, raretés, qualités, etc.)
    depuis les fichiers JSON du projet original.
    À appeler une seule fois lors du premier déploiement.
    """
    from app.seed.seed_data import seed_reference_data
    try:
        await seed_reference_data(session)
        return MessageResponse(message="Données de référence insérées avec succès !")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur seed: {str(e)}")


@router.post("/migrate-players", response_model=MessageResponse)
async def migrate_players(
    session: AsyncSession = Depends(get_session),
):
    """
    Migre les sauvegardes joueurs existantes (accounts.json + player_save.json).
    À appeler après le seed pour transférer les données des joueurs.
    """
    from app.seed.seed_data import migrate_player_saves
    try:
        count = await migrate_player_saves(session)
        return MessageResponse(message=f"{count} joueur(s) migré(s) avec succès !")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur migration: {str(e)}")
