"""
Jetons envoyés par e-mail : lien de confirmation d'adresse et code de
récupération de mot de passe. Seul le hash est stocké.
"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field

PURPOSE_VERIFY_EMAIL = "verify_email"
PURPOSE_RESET_PASSWORD = "reset_password"


class EmailToken(SQLModel, table=True):
    __tablename__ = "email_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    purpose: str = Field(max_length=20)
    token_hash: str = Field(max_length=128, index=True)
    # Adresse visée au moment de l'envoi : un changement d'e-mail ultérieur
    # invalide le lien de confirmation de l'ancienne adresse.
    email: str = Field(default="", max_length=254)
    attempts: int = Field(default=0)
    expires_at: datetime
    used_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
