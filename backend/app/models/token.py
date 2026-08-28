"""
Modèle RefreshToken — Pour la rotation JWT.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(max_length=256)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relations
    user: Optional["User"] = Relationship(back_populates="refresh_tokens")
