"""
Routes d'authentification — Register, Login, Refresh.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    MessageResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()
auth_service = AuthService()


@router.post("/register", response_model=MessageResponse)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    """Inscription d'un nouveau joueur."""
    user = await auth_service.register(
        session, request.username, request.password
    )
    return MessageResponse(
        message=f"Compte créé avec succès ! Bienvenue {user.display_name}."
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Connexion — retourne un access token + refresh token."""
    tokens = await auth_service.login(
        session, request.username, request.password
    )
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Renouvelle les tokens via un refresh token valide."""
    tokens = await auth_service.refresh_tokens(
        session, request.refresh_token
    )
    return TokenResponse(**tokens)
