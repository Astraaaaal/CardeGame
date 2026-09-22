"""
Schemas d'authentification — Request / Response.
"""

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9]+$")
    password: str = Field(min_length=4, max_length=100)
    email: str = Field(min_length=3, max_length=254)
    # Consentement explicite (RGPD) : décoché par défaut côté interface.
    newsletter: bool = False
    # Requis uniquement si settings.BETA_INVITE_CODE est configuré (cf. app/api/auth.py).
    invite_code: str = Field(default="", max_length=50)


class LoginRequest(BaseModel):
    username: str = Field(max_length=254)  # pseudo OU adresse e-mail
    password: str = Field(max_length=200)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=200)


class PasswordResetRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)  # pseudo ou e-mail


class PasswordResetConfirm(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")
    new_password: str = Field(min_length=4, max_length=100)


class ChangeEmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(max_length=200)


class NewsletterRequest(BaseModel):
    subscribed: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(max_length=2000)


class MessageResponse(BaseModel):
    message: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=4, max_length=100)


class DeleteAccountRequest(BaseModel):
    password: str = Field(max_length=200)
