"""
Routes admin — Seed des données, utilitaires.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.core.dependencies import require_admin
from app.schemas.auth import MessageResponse
from app.models.distinction import Distinction, UserDistinction
from app.models.game_config import GameConfig
from app.models.user import User
from app.services import distinctions, game_status, season_reset

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


class GrantDistinctionBody(BaseModel):
    distinction_id: str
    # Trace lisible dans la table d'attribution (« cadeau de réouverture »).
    reason: str | None = None


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


@router.get("/distinctions")
async def list_distinctions(session: AsyncSession = Depends(get_session)):
    """Toutes les distinctions existantes, avec le nombre de joueurs qui les portent."""
    rows = (await session.execute(select(Distinction).order_by(Distinction.sort_order))).scalars().all()
    counts = dict((await session.execute(
        select(UserDistinction.distinction_id, func.count())
        .group_by(UserDistinction.distinction_id)
    )).all())
    return [
        {"id": d.id, "name": d.name, "description": d.description, "color": d.color,
         "active": d.active, "holders": counts.get(d.id, 0)}
        for d in rows
    ]


@router.post("/distinctions/grant-all")
async def grant_distinction_to_all(
    body: GrantDistinctionBody, session: AsyncSession = Depends(get_session),
):
    """Attribue une distinction à **tous les comptes existants** (cadeau de
    réouverture). Idempotent : relancer ne crée pas de doublon et ne retire
    rien. À lancer APRÈS la remise à zéro — elle ne touche pas aux
    distinctions, mais l'ordre reste le bon pour que le cadeau soit visible."""
    if not await session.get(Distinction, body.distinction_id):
        raise HTTPException(404, "Distinction inconnue.")
    user_ids = (await session.execute(select(User.id))).scalars().all()
    granted = await distinctions.grant_many(
        session, list(user_ids), body.distinction_id, reason=body.reason,
    )
    await session.commit()
    return {"accounts": len(user_ids), "granted": granted}


@router.post("/reset-accounts")
async def reset_accounts(body: ResetBody, session: AsyncSession = Depends(get_session)):
    """Remet tous les comptes à zéro (garde comptes, réglages et amis) et déconnecte tout le monde."""
    if body.confirm.strip() != RESET_CONFIRM_WORD:
        raise HTTPException(400, f"Tape {RESET_CONFIRM_WORD} pour confirmer.")
    return await season_reset.reset_all_accounts(session)
