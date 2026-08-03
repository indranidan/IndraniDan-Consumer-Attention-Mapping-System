"""
Application Configuration
=========================
Loads all settings from environment variables using Pydantic Settings.
Provides a cached singleton via get_settings() for dependency injection.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration loaded from .env file.
    All values have sensible defaults for local development.
    """

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/consumer_attention_db"

    # ── JWT ───────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Google OAuth 2.0 ─────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── Application ───────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Pydantic Settings Config ──────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Uses lru_cache so the .env file is only read once per process.
    """
    return Settings()
