"""
Configuration centralisée — chargée depuis les variables d'environnement.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Environnement ──
    ENVIRONMENT: str = "development"  # "production" sur Render

    # ── Database ──
    DATABASE_URL: str = "postgresql+asyncpg://cardegame_user:password@localhost:5432/cardegame"

    # ── JWT ──
    JWT_SECRET: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Bcrypt ──
    BCRYPT_ROUNDS: int = 12

    # ── Admin (protège /api/admin/*) ──
    ADMIN_KEY: str = ""  # vide = routes admin refusées

    # ── Bêta (protège /api/auth/register) ──
    BETA_INVITE_CODE: str = ""  # vide = inscription libre (pas de gate)

    # ── Cloudinary (vide = rendu des cartes côté client) ──
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── URL publique du jeu (liens dans les e-mails, retour de paiement) ──
    PUBLIC_APP_URL: str = "http://localhost:5173"

    # ── E-mails / newsletter (Brevo) — vide = e-mails écrits dans les logs ──
    BREVO_API_KEY: str = ""
    # Texte (et non entier) : une variable vide sur Render ne doit pas empêcher le démarrage.
    BREVO_NEWSLETTER_LIST_ID: str = ""  # vide = pas de synchronisation newsletter
    EMAIL_SENDER_ADDRESS: str = "no-reply@cardegame.local"
    EMAIL_SENDER_NAME: str = "CardeGame"

    # ── Paiements (Stripe) — vide = achats en euros refusés ──
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # ── CORS ── (JSON en variable d'env : '["https://mon-site.fr"]')
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # Les réglages de gameplay (récompense quotidienne, etc.) vivent en base
    # (cf. app/models/game_config.py), éditables depuis l'admin — pas ici.

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore les variables d'env non déclarées (Render en injecte)
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
