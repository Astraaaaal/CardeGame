"""
Sécurité — Hashing bcrypt + JWT.
"""

import hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password ──

def hash_password(password: str) -> str:
    """Hash un mot de passe avec bcrypt (salt inclus automatiquement)."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt."""
    return pwd_context.verify(plain_password, hashed_password)


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
