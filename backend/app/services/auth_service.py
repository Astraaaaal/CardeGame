"""
AuthService — Gestion de l'inscription, connexion, refresh tokens.
"""

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.token import RefreshToken
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
)


class AuthService:

    async def register(
        self, session: AsyncSession, username: str, password: str
    ) -> User:
        """Crée un nouveau compte."""
        username_lower = username.strip().lower()

        # Vérifier unicité
        result = await session.execute(
            select(User).where(User.username == username_lower)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce pseudo est déjà pris.",
            )

        user = User(
            username=username_lower,
            display_name=username.strip(),
            password_hash=hash_password(password),
            coins=500,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def login(
        self, session: AsyncSession, username: str, password: str
    ) -> dict:
        """
        Vérifie les identifiants, retourne les tokens JWT.
        """
        username_lower = username.strip().lower()

        result = await session.execute(
            select(User).where(User.username == username_lower)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identifiants incorrects.",
            )

        # Mettre à jour last_login
        user.last_login = datetime.utcnow()

        # Générer les tokens
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)

        # Stocker le refresh token hashé
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=datetime.utcfromtimestamp(decode_token(refresh)["exp"]),
        )
        session.add(refresh_record)
        await session.commit()

        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }

    async def logout(
        self, session: AsyncSession, refresh_token_str: str
    ) -> None:
        """Révoque un refresh token (best-effort : pas d'erreur s'il est inconnu)."""
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == hash_token(refresh_token_str)
            )
        )
        stored = result.scalar_one_or_none()
        if stored:
            await session.delete(stored)
            await session.commit()

    async def refresh_tokens(
        self, session: AsyncSession, refresh_token_str: str
    ) -> dict:
        """
        Vérifie un refresh token et émet une nouvelle paire.
        L'ancien refresh token est invalidé (rotation).
        """
        payload = decode_token(refresh_token_str)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token invalide.",
            )

        user_id = int(payload["sub"])
        token_hash = hash_token(refresh_token_str)

        # Trouver le token en BDD
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.token_hash == token_hash,
            )
        )
        stored = result.scalar_one_or_none()

        if not stored:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inconnu ou déjà utilisé.",
            )

        # Supprimer l'ancien (rotation)
        await session.delete(stored)

        # Émettre de nouveaux tokens
        new_access = create_access_token(user_id)
        new_refresh = create_refresh_token(user_id)

        new_record = RefreshToken(
            user_id=user_id,
            token_hash=hash_token(new_refresh),
            expires_at=datetime.utcfromtimestamp(decode_token(new_refresh)["exp"]),
        )
        session.add(new_record)
        await session.commit()

        return {
            "access_token": new_access,
            "refresh_token": new_refresh,
            "token_type": "bearer",
        }
