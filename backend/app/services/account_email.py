"""
Adresse e-mail d'un compte : confirmation par lien, changement d'adresse,
newsletter et récupération de mot de passe par code à 6 chiffres.
"""

import hashlib
import html
import re
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.core.security import hash_password, verify_password
from app.models.email_token import EmailToken, PURPOSE_RESET_PASSWORD, PURPOSE_VERIFY_EMAIL
from app.models.token import RefreshToken
from app.models.user import User
from app.services.email_sender import send_email, sync_newsletter

VERIFY_LINK_VALIDITY = timedelta(hours=48)
RESET_CODE_VALIDITY = timedelta(minutes=15)
RESET_CODE_MAX_ATTEMPTS = 5
# Plafond de codes envoyés par compte : 5 essais × 5 codes/h laisse ~1 chance sur 40 000/h.
RESET_CODES_PER_HOUR = 5

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def normalize_email(raw: str) -> str:
    email = raw.strip().lower()
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise HTTPException(400, "Adresse e-mail invalide.")
    return email


async def ensure_email_available(session: AsyncSession, email: str, exclude_user_id: int | None = None) -> None:
    query = select(User.id).where(User.email == email)
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    if (await session.execute(query)).first():
        raise HTTPException(409, "Cette adresse e-mail est déjà utilisée.")


async def find_user_by_identifier(session: AsyncSession, identifier: str) -> User | None:
    """Pseudo ou e-mail (contient « @ »)."""
    value = identifier.strip().lower()
    column = User.email if "@" in value else User.username
    return (await session.execute(select(User).where(column == value))).scalar_one_or_none()


async def send_verification(session: AsyncSession, user: User) -> None:
    """Invalide les liens précédents et envoie un nouveau lien de confirmation. Commit."""
    if not user.email:
        raise HTTPException(400, "Aucune adresse e-mail à confirmer.")
    await session.execute(delete(EmailToken).where(
        EmailToken.user_id == user.id, EmailToken.purpose == PURPOSE_VERIFY_EMAIL,
    ))
    token = secrets.token_urlsafe(32)
    session.add(EmailToken(
        user_id=user.id, purpose=PURPOSE_VERIFY_EMAIL, token_hash=_hash(token),
        email=user.email, expires_at=datetime.utcnow() + VERIFY_LINK_VALIDITY,
    ))
    await session.commit()
    link = f"{settings.PUBLIC_APP_URL.rstrip('/')}/verify-email?token={token}"
    await send_email(
        user.email, "Confirme ton adresse e-mail — CardeGame", "Confirme ton adresse e-mail",
        f"<p>Bonjour {html.escape(user.display_name)},</p><p>Clique sur le bouton ci-dessous pour confirmer ton adresse.</p>"
        f"<p><a href=\"{link}\" style=\"background:#4f46e5;color:#fff;padding:10px 18px;border-radius:8px;"
        f"text-decoration:none\">Confirmer mon adresse</a></p>"
        f"<p style=\"font-size:12px;color:#888\">Lien valable 48 h.</p>",
    )


async def confirm_email(session: AsyncSession, token: str) -> User:
    row = (await session.execute(select(EmailToken).where(
        EmailToken.token_hash == _hash(token), EmailToken.purpose == PURPOSE_VERIFY_EMAIL,
    ))).scalar_one_or_none()
    if not row or row.used_at or row.expires_at < datetime.utcnow():
        raise HTTPException(400, "Lien de confirmation invalide ou expiré.")
    user = await session.get(User, row.user_id)
    if not user or user.email != row.email:
        raise HTTPException(400, "Ce lien ne correspond plus à l'adresse de ton compte.")
    user.email_verified_at = datetime.utcnow()
    row.used_at = datetime.utcnow()
    session.add_all([user, row])
    await session.commit()
    if user.newsletter_opt_in:
        await sync_newsletter(user.email, True, user.username)
    return user


async def change_email(session: AsyncSession, user: User, new_email: str, password: str) -> None:
    if not verify_password(password, user.password_hash):
        raise HTTPException(400, "Mot de passe incorrect.")
    email = normalize_email(new_email)
    if email == user.email:
        raise HTTPException(400, "C'est déjà ton adresse actuelle.")
    await ensure_email_available(session, email, exclude_user_id=user.id)
    previous = user.email
    user.email = email
    user.email_verified_at = None
    session.add(user)
    await session.commit()
    if previous and user.newsletter_opt_in:
        await sync_newsletter(previous, False)
    await send_verification(session, user)


async def set_newsletter(session: AsyncSession, user: User, subscribed: bool) -> None:
    user.newsletter_opt_in = subscribed
    session.add(user)
    await session.commit()
    # Une adresse non confirmée n'est inscrite qu'à sa confirmation (cf. confirm_email).
    if user.email_verified_at or not subscribed:
        await sync_newsletter(user.email, subscribed, user.username)


async def request_password_reset(session: AsyncSession, identifier: str) -> None:
    """Envoie un code si le compte existe et a une adresse confirmée. Ne révèle jamais
    si le compte existe (même réponse côté route dans tous les cas)."""
    user = await find_user_by_identifier(session, identifier)
    if not user or not user.email or not user.email_verified_at:
        return
    now = datetime.utcnow()
    sent_last_hour = (await session.execute(select(func.count()).select_from(EmailToken).where(
        EmailToken.user_id == user.id, EmailToken.purpose == PURPOSE_RESET_PASSWORD,
        EmailToken.created_at > now - timedelta(hours=1),
    ))).scalar() or 0
    if sent_last_hour >= RESET_CODES_PER_HOUR:
        return
    # Les codes précédents sont invalidés mais conservés (ils comptent dans le plafond).
    await session.execute(update(EmailToken).where(
        EmailToken.user_id == user.id, EmailToken.purpose == PURPOSE_RESET_PASSWORD, EmailToken.used_at.is_(None),
    ).values(used_at=now))
    code = f"{secrets.randbelow(1_000_000):06d}"
    session.add(EmailToken(
        user_id=user.id, purpose=PURPOSE_RESET_PASSWORD, token_hash=_hash(code),
        email=user.email, expires_at=datetime.utcnow() + RESET_CODE_VALIDITY,
    ))
    await session.commit()
    await send_email(
        user.email, f"{code} — ton code de récupération CardeGame", "Récupération de mot de passe",
        f"<p>Bonjour {html.escape(user.display_name)},</p><p>Voici ton code pour choisir un nouveau mot de passe :</p>"
        f"<p style=\"font-size:32px;font-weight:bold;letter-spacing:6px\">{code}</p>"
        f"<p style=\"font-size:12px;color:#888\">Code valable 15 minutes.</p>",
    )


async def confirm_password_reset(session: AsyncSession, identifier: str, code: str, new_password: str) -> None:
    invalid = HTTPException(400, "Code invalide ou expiré.")
    user = await find_user_by_identifier(session, identifier)
    if not user:
        raise invalid
    row = (await session.execute(select(EmailToken).where(
        EmailToken.user_id == user.id, EmailToken.purpose == PURPOSE_RESET_PASSWORD, EmailToken.used_at.is_(None),
    ).order_by(EmailToken.created_at.desc()))).scalars().first()
    if not row or row.expires_at < datetime.utcnow() or row.attempts >= RESET_CODE_MAX_ATTEMPTS:
        raise invalid
    if row.token_hash != _hash(code.strip()):
        row.attempts += 1
        session.add(row)
        await session.commit()
        raise invalid

    user.password_hash = hash_password(new_password)
    row.used_at = datetime.utcnow()
    session.add_all([user, row])
    # Toutes les sessions ouvertes sont déconnectées.
    await session.execute(delete(RefreshToken).where(RefreshToken.user_id == user.id))
    await session.commit()


async def purge_for_user(session: AsyncSession, user: User) -> None:
    """Suppression de compte : jetons + désinscription newsletter. Ne commit pas."""
    await session.execute(delete(EmailToken).where(EmailToken.user_id == user.id))
    if user.newsletter_opt_in:
        await sync_newsletter(user.email, False)
