"""
Sécurité — Hashing bcrypt + JWT.
"""

import hashlib
from datetime import datetime, timedelta

import bcrypt
from jose import jwt, JWTError
from app.config import settings


# ── Password ──
# On utilise la lib `bcrypt` directement (passlib 1.7.4 est abandonné et casse
# avec bcrypt >= 5). bcrypt ignore les octets au-delà de 72 : on tronque
# explicitement pour rester déterministe et éviter le ValueError de bcrypt >= 5.

def _pw_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:72]


def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt (salt inclus automatiquement)."""
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    return bcrypt.hashpw(_pw_bytes(password), salt).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt."""
    try:
        return bcrypt.checkpw(_pw_bytes(plain_password), hashed_password.encode("ascii"))
    except (ValueError, TypeError):
        return False


# ── JWT ──

def create_access_token(user_id: int) -> str:
    """Crée un JWT d'accès court (30 min par défaut)."""
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Crée un JWT de refresh long (30 jours par défaut)."""
    expire = datetime.utcnow() + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Décode un JWT. Retourne None si invalide ou expiré."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash un refresh token pour stockage en BDD (SHA-256)."""
    return hashlib.sha256(token.encode()).hexdigest()
