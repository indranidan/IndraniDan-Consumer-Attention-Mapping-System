"""
Application Configuration
=========================
Loads all settings from environment variables using Pydantic Settings.
Provides a cached singleton via get_settings() for dependency injection.
"""

from functools import lru_cache
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration loaded from .env file.
    All values have sensible defaults for local development.
    """

    # ── Database (Relational PostgreSQL) ──────────────────────
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/consumer_attention_db"

    # ── Database (Document & Time-Series MongoDB) ─────────────
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "consumer_attention_ai_db"

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

    # ── AI Module ─────────────────────────────────────────────
    AI_OUTPUT_PATH: str = "storage/outputs/ai_jobs"
    AI_INPUT_PATH: str = "storage/uploads"
    AI_PIPELINE_TIMEOUT: int = 3600
    AI_MAX_CONCURRENT_JOBS: int = 1
    WEBCAM_DEVICE: int = 0

    # ── Pydantic Settings Config ──────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
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
