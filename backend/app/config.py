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

    # ── Cloudinary (vide = rendu des cartes côté client) ──
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # ── CORS ── (JSON en variable d'env : '["https://mon-site.fr"]')
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Game ──
    DAILY_BASE_REWARD: int = 500
    DAILY_STREAK_BONUS: int = 100

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore les variables d'env non déclarées (Render en injecte)
    )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


settings = Settings()
