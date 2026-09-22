"""
Routes d'authentification — Register, Login, Refresh, Logout.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.core.ratelimit import rate_limit
from app.core.security import same_secret
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    MessageResponse,
    VerifyEmailRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.services import account_email, game_status
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/status")
async def public_status(session: AsyncSession = Depends(get_session)):
    """État public du jeu (fermé ou non, message affiché sur la page de connexion)."""
    return await game_status.get_status(session)


auth_service = AuthService()


@router.post(
    "/register",
    response_model=MessageResponse,
    dependencies=[Depends(rate_limit(5, 60))],
)
async def register(
    request: RegisterRequest,
    session: AsyncSession = Depends(get_session),
    x_admin_key: str = Header(default=""),
):
    """Inscription d'un nouveau joueur."""
    await game_status.ensure_open(session, x_admin_key)
    if settings.BETA_INVITE_CODE and not same_secret(request.invite_code.strip(), settings.BETA_INVITE_CODE):
        raise HTTPException(status_code=403, detail="Code d'invitation invalide.")
    user = await auth_service.register(
        session, request.username, request.password, request.email, request.newsletter,
    )
    await account_email.send_verification(session, user)
    return MessageResponse(
        message=f"Compte créé avec succès ! Bienvenue {user.display_name}. "
                f"Un lien de confirmation a été envoyé à {user.email}."
    )


@router.post("/verify-email", response_model=MessageResponse, dependencies=[Depends(rate_limit(20, 60))])
async def verify_email(request: VerifyEmailRequest, session: AsyncSession = Depends(get_session)):
    """Confirme une adresse e-mail à partir du lien reçu."""
    user = await account_email.confirm_email(session, request.token)
    return MessageResponse(message=f"Adresse {user.email} confirmée !")


@router.post("/password-reset/request", response_model=MessageResponse, dependencies=[Depends(rate_limit(5, 900))])
async def request_password_reset(request: PasswordResetRequest, session: AsyncSession = Depends(get_session)):
    """Envoie un code à 6 chiffres. Réponse identique que le compte existe ou non."""
    await account_email.request_password_reset(session, request.identifier)
    return MessageResponse(
        message="Si un compte avec une adresse confirmée correspond, un code vient d'être envoyé par e-mail."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse, dependencies=[Depends(rate_limit(10, 900))])
async def confirm_password_reset(request: PasswordResetConfirm, session: AsyncSession = Depends(get_session)):
    await account_email.confirm_password_reset(session, request.identifier, request.code, request.new_password)
    return MessageResponse(message="Mot de passe modifié. Tu peux te connecter.")


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit(10, 60))],
)
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session),
    x_admin_key: str = Header(default=""),
):
    """Connexion — retourne un access token + refresh token."""
    await game_status.ensure_open(session, x_admin_key)
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
    x_admin_key: str = Header(default=""),
):
    """Renouvelle les tokens via un refresh token valide."""
    await game_status.ensure_open(session, x_admin_key)
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
