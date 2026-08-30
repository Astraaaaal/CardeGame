"""
Routes d'authentification — Register, Login, Refresh, Logout.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.core.ratelimit import rate_limit
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


@router.post(
    "/register",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(5, 60))],
)
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


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(10, 60))],
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Connexion — retourne un access token + refresh token."""
    tokens = await auth_service.login(
        session, request.username, request.password
    )
    return TokenResponse(**tokens)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(30, 60))],
)
async def refresh(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Renouvelle les tokens via un refresh token valide."""
    tokens = await auth_service.refresh_tokens(
        session, request.refresh_token
    )
    return TokenResponse(**tokens)


@router.post(
    "/logout",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(20, 60))],
)
async def logout(
    request: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Déconnexion — révoque le refresh token fourni."""
    await auth_service.logout(session, request.refresh_token)
    return MessageResponse(message="Déconnecté.")
