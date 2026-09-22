"""
AuthService — Gestion de l'inscription, connexion, refresh tokens.
"""

from datetime import datetime
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status

from app.models.user import User
from app.models.token import RefreshToken
from app.models.economy import Resource, UserResource
from app.services.wallet import COINS_ID
from app.services import account_email, names
from app.core import ratelimit
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
        self, session: AsyncSession, username: str, password: str, email: str, newsletter: bool = False,
    ) -> User:
        """Crée un nouveau compte."""
        username_lower = username.strip().lower()
        names.ensure_not_reserved(username_lower)

        # Vérifier unicité
        result = await session.execute(
            select(User).where(User.username == username_lower)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce pseudo est déjà pris.",
            )

        email = account_email.normalize_email(email)
        await account_email.ensure_email_available(session, email)

        resources = (await session.execute(select(Resource))).scalars().all()
        coins_start = next((r.starting_amount for r in resources if r.id == COINS_ID), 500)

        user = User(
            username=username_lower,
            display_name=username.strip(),
            password_hash=hash_password(password),
            email=email,
            newsletter_opt_in=newsletter,
            coins=coins_start,
            created_at=datetime.utcnow(),
        )
        session.add(user)
        await session.flush()  # pour obtenir user.id

        for r in resources:
            if r.id != COINS_ID and r.starting_amount > 0:
                session.add(UserResource(user_id=user.id, resource_id=r.id, amount=r.starting_amount))

        await session.commit()
        await session.refresh(user)
        return user

    async def login(
        self, session: AsyncSession, username: str, password: str
    ) -> dict:
        """
        Vérifie les identifiants, retourne les tokens JWT.
        """
        # Plafond d'échecs par compte, en plus de la limite par IP de la route.
        account_key = username.strip().lower()
        if ratelimit.login_blocked(account_key):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives sur ce compte : réessaie dans quelques minutes.",
            )
        user = await account_email.find_user_by_identifier(session, username)

        if not user or not verify_password(password, user.password_hash):
            ratelimit.record_login_failure(account_key)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identifiants incorrects.",
            )
        ratelimit.clear_login_failures(account_key)

        # Mettre à jour last_login ; les sessions expirées du compte sont purgées.
        user.last_login = datetime.utcnow()
        await session.execute(delete(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.expires_at < datetime.utcnow(),
        ))

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
        await session.execute(
            delete(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token_str))
        )
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

        # Rotation : l'ancien token est supprimé en une requête atomique — deux
        # renouvellements simultanés avec le même token n'en valident qu'un.
        consumed = (await session.execute(
            delete(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.token_hash == token_hash,
            ).returning(RefreshToken.id).execution_options(synchronize_session=False)
        )).first()

        if not consumed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inconnu ou déjà utilisé.",
            )

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
