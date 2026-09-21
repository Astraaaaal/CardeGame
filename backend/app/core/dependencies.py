"""
Dependencies FastAPI — Injection du user authentifié.
"""

from datetime import datetime

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_session
from app.core.security import decode_token
from app.models.user import User
from app.services import game_status
from app.services.presence import LAST_SEEN_THROTTLE_S

bearer_scheme = HTTPBearer()



async def require_admin(x_admin_key: str = Header(default="")):
    """
    Protège les routes /api/admin/*. Exige l'en-tête `X-Admin-Key` égal à
    `settings.ADMIN_KEY`. Si `ADMIN_KEY` n'est pas configuré, tout est refusé.
    """
    if not settings.ADMIN_KEY or x_admin_key != settings.ADMIN_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé admin invalide ou manquante.",
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
    x_admin_key: str = Header(default=""),
) -> User:
    """
    Extrait et vérifie le JWT Bearer, retourne le User correspondant.
    Utilisable comme dependency dans les routes protégées.
    """
    await game_status.ensure_open(session, x_admin_key)
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de type invalide (access attendu)",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token malformé",
        )

    result = await session.execute(
        select(User).where(User.id == int(user_id))
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
        )

    now = datetime.utcnow()
    if not user.last_seen or (now - user.last_seen).total_seconds() > LAST_SEEN_THROTTLE_S:
        user.last_seen = now
        session.add(user)
        await session.commit()

    return user
