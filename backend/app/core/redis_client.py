"""
Resilient Redis Client
======================
Provides a singleton Redis connection with lazy reconnection, cooldown-based
retry logic, and a live health probe. Starting or restarting Redis after the
backend is already running will automatically restore the connection without
requiring a server restart.
"""

import os
import time
import logging

# pyrefly: ignore [missing-import]
import redis

logger = logging.getLogger(__name__)

def _resolve_redis_url() -> str:
    try:
        from app.core.config import get_settings
        url = get_settings().REDIS_URL
    except Exception:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    if not url:
        url = "redis://localhost:6379/0"
    # Upstash requires SSL (rediss://)
    if "upstash.io" in url and url.startswith("redis://"):
        url = "rediss://" + url[len("redis://"):]
    return url


# Minimum seconds between reconnection attempts to avoid log spam
_RECONNECT_COOLDOWN_SECONDS = 10.0


class RedisClient:
    """
    Lazy, resilient Redis connection manager.

    * On first call to ``get_instance()`` a connection is attempted.
    * If the connection fails, ``None`` is returned and no retry is made
      until ``_RECONNECT_COOLDOWN_SECONDS`` have elapsed.
    * If the connection succeeds, subsequent calls return the cached client.
    * ``is_available()`` performs a live ``PING`` and resets the client on
      failure so the next call will attempt to reconnect.
    """

    _instance: redis.Redis | None = None
    _last_attempt: float = 0.0

    @classmethod
    def get_instance(cls) -> redis.Redis | None:
        """Return the cached Redis client, or attempt to connect if needed."""
        if cls._instance is not None:
            return cls._instance

        now = time.monotonic()
        if now - cls._last_attempt < _RECONNECT_COOLDOWN_SECONDS:
            return None  # still within cooldown

        cls._last_attempt = now
        url = _resolve_redis_url()
        try:
            client = redis.Redis.from_url(url, decode_responses=True)
            client.ping()
            cls._instance = client
            # Hide credentials when logging URL
            safe_url = url.split("@")[-1] if "@" in url else url
            logger.info(f"Connected to Redis at {safe_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}). Operating in fallback mode.")
            cls._instance = None

        return cls._instance

    @classmethod
    def is_available(cls) -> bool:
        """
        Live health probe: return *True* only if Redis responds to PING.
        Resets the cached client on failure so that reconnection is attempted
        after the cooldown elapses.
        """
        client = cls.get_instance()
        if client is None:
            return False
        try:
            client.ping()
            return True
        except Exception:
            cls._instance = None
            cls._last_attempt = time.monotonic()
            return False

    @classmethod
    def reset(cls) -> None:
        """Force-drop the cached connection (useful for tests)."""
        cls._instance = None
        cls._last_attempt = 0.0


def get_redis_client() -> redis.Redis | None:
    """Convenience accessor used throughout the codebase."""
    return RedisClient.get_instance()


def is_redis_available() -> bool:
    """Live health check — returns *True* only when Redis responds."""
    return RedisClient.is_available()


# Eager first attempt (matches original import-time behavior).
# The result may be None if Redis is not running — that is fine.
redis_client = get_redis_client()
