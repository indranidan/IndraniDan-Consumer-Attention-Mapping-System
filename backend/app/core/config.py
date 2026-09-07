"""
Application Configuration
=========================
Loads all settings from environment variables using Pydantic Settings.
Provides a cached singleton via get_settings() for dependency injection.
"""

from functools import lru_cache
# pyrefly: ignore [missing-import]
from pydantic_settings import BaseSettings, SettingsConfigDict


from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent


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

    # ── Redis / Event Broker ──────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Google OAuth 2.0 ─────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # ── Application ───────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    ENVIRONMENT: str = "development"

    # ── AI Module ─────────────────────────────────────────────
    AI_OUTPUT_PATH: str = "storage/outputs/ai_jobs"
    AI_INPUT_PATH: str = "storage/uploads"
    REPORTS_OUTPUT_PATH: str = "storage/outputs/reports"
    AI_PIPELINE_TIMEOUT: int = 3600
    AI_MAX_CONCURRENT_JOBS: int = 1
    WEBCAM_DEVICE: int = 0

    # ── Pydantic Settings Config ──────────────────────────────
    model_config = SettingsConfigDict(
        env_file=(
            str(_ROOT_DIR / ".env"),
            str(_BACKEND_DIR / ".env"),
            ".env",
        ),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


# Insecure default keys that must never be used in production
_INSECURE_SECRET_KEYS = {"change-this-in-production", "secret", ""}


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Uses lru_cache so the .env file is only read once per process.
    """
    s = Settings()

    # Production secret key guard
    if s.ENVIRONMENT.lower() == "production" and s.SECRET_KEY in _INSECURE_SECRET_KEYS:
        import logging
        logger = logging.getLogger("security")
        msg = (
            "CRITICAL SECURITY WARNING: Running in production mode with an insecure default SECRET_KEY. "
            "Set a strong, unique SECRET_KEY environment variable before deploying to production."
        )
        logger.critical(msg)
        print(f"[SECURITY] {msg}")

    return s
