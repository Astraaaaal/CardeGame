"""
Routes admin — Seed des données, utilitaires.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.dependencies import require_admin
from app.schemas.auth import MessageResponse
from app.models.game_config import GameConfig
from app.services import game_status, season_reset

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


class GameStatusBody(BaseModel):
    closed: bool
    message: str = Field(default="", max_length=1000)


class ResetBody(BaseModel):
    confirm: str


RESET_CONFIRM_WORD = "REINITIALISER"


@router.get("/game-status")
async def get_game_status(session: AsyncSession = Depends(get_session)):
    """Jeu fermé ou non, et message affiché (vide = message par défaut)."""
    config = await session.get(GameConfig, 1)
    return {
        "closed": bool(config and config.game_closed),
        "message": config.closed_message if config else "",
        "default_message": game_status.DEFAULT_CLOSED_MESSAGE,
    }


@router.put("/game-status")
async def set_game_status(body: GameStatusBody, session: AsyncSession = Depends(get_session)):
    config = await session.get(GameConfig, 1) or GameConfig(id=1)
    config.game_closed = body.closed
    config.closed_message = body.message.strip()
    session.add(config)
    await session.commit()
    game_status.invalidate()
    return await get_game_status(session)


@router.post("/reset-accounts")
async def reset_accounts(body: ResetBody, session: AsyncSession = Depends(get_session)):
    """Remet tous les comptes à zéro (garde comptes, réglages et amis) et déconnecte tout le monde."""
    if body.confirm.strip() != RESET_CONFIRM_WORD:
        raise HTTPException(400, f"Tape {RESET_CONFIRM_WORD} pour confirmer.")
    return await season_reset.reset_all_accounts(session)
