"""
MongoDB Database Engine & Connection Lifecycle
==============================================
Provides asynchronous MongoDB connection pooling using Motor,
request-scoped dependency injection for FastAPI endpoints,
and synchronous PyMongo helper for background workers.
Includes cloud-ready TLS/SSL configuration with certifi and auto-indexing.
"""

import logging
from typing import Any, Dict, Optional
# pyrefly: ignore [missing-import]
import pymongo
# pyrefly: ignore [missing-import]
from pymongo.database import Database as SyncDatabase
# pyrefly: ignore [missing-import]
import motor.motor_asyncio
# pyrefly: ignore [missing-import]
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

logger = logging.getLogger("mongodb")

_async_client: Optional[AsyncIOMotorClient] = None
_sync_client: Optional[pymongo.MongoClient] = None


def _get_client_options(url: str, timeout_ms: int = 5000) -> Dict[str, Any]:
    """
    Build connection options resilient to cloud hosts (MongoDB Atlas, Railway, etc.).
    Supplies the certifi CA root bundle for secure TLS/SSL handshakes on Windows/Linux.
    """
    options: Dict[str, Any] = {
        "serverSelectionTimeoutMS": timeout_ms,
        "connectTimeoutMS": 10000,
        "socketTimeoutMS": 30000,
    }

    # Automatically attach certifi CA bundle for cloud/TLS connections
    if "mongodb+srv://" in url or "ssl=true" in url.lower() or "tls=true" in url.lower():
        try:
            # pyrefly: ignore [missing-import]
            import certifi
            options["tlsCAFile"] = certifi.where()
        except ImportError:
            pass

    return options


async def init_mongo_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure indexes exist for high-throughput query and aggregation performance."""
    try:
        # ai_tracks: compound lookup by job and track/frame
        await db["ai_tracks"].create_index([("job_id", pymongo.ASCENDING), ("track_id", pymongo.ASCENDING)])
        await db["ai_tracks"].create_index([("job_id", pymongo.ASCENDING), ("frame_idx", pymongo.ASCENDING)])

        # shopper_journeys: lookup by job and tracking_id
        await db["shopper_journeys"].create_index([("job_id", pymongo.ASCENDING), ("tracking_id", pymongo.ASCENDING)])

        # attention_events: lookup by job
        await db["attention_events"].create_index([("job_id", pymongo.ASCENDING)])
        await db["attention_events"].create_index([("job_id", pymongo.ASCENDING), ("event_id", pymongo.ASCENDING)])

        # interaction_events: lookup by job and event
        await db["interaction_events"].create_index([("job_id", pymongo.ASCENDING)])
        await db["interaction_events"].create_index([("job_id", pymongo.ASCENDING), ("event_id", pymongo.ASCENDING)])

        # Unique summaries by job_id
        await db["job_reports"].create_index("job_id", unique=True)
        await db["m4_analyses"].create_index("job_id", unique=True)
        await db["m5_analyses"].create_index("job_id", unique=True)

        logger.info("MongoDB collections and indexes initialized successfully.")
    except Exception as exc:
        logger.warning(f"Could not initialize MongoDB indexes: {exc}")


async def connect_mongo() -> Optional[AsyncIOMotorClient]:
    """
    Initialize the asynchronous MongoDB client and verify connectivity.
    Called during FastAPI lifespan startup.
    """
    global _async_client
    settings = get_settings()
    try:
        # Mask credentials in logs for security
        url_display = settings.MONGODB_URL.split("@")[-1] if "@" in settings.MONGODB_URL else settings.MONGODB_URL
        logger.info(f"Connecting to MongoDB at {url_display}...")

        opts = _get_client_options(settings.MONGODB_URL, timeout_ms=5000)
        _async_client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=50,
            minPoolSize=5,
            **opts,
        )
        # Verify connectivity
        await _async_client.admin.command("ping")
        logger.info(f"MongoDB connected successfully. Database: {settings.MONGODB_DB_NAME}")

        # Initialize collections and indexes
        db = _async_client[settings.MONGODB_DB_NAME]
        await init_mongo_indexes(db)

        return _async_client
    except Exception as exc:
        logger.warning(
            f"MongoDB connection unavailable ({exc}). Running in graceful local storage / fallback mode."
        )
        return None


async def close_mongo() -> None:
    """
    Close the asynchronous and synchronous MongoDB clients.
    Called during FastAPI lifespan shutdown.
    """
    global _async_client, _sync_client
    if _async_client:
        _async_client.close()
        _async_client = None
        logger.info("Async MongoDB connection closed.")
    if _sync_client:
        _sync_client.close()
        _sync_client = None
        logger.info("Sync MongoDB connection closed.")


def get_mongo_client() -> Optional[AsyncIOMotorClient]:
    """Get the current async MongoDB client instance."""
    return _async_client


def get_mongo_db() -> Optional[AsyncIOMotorDatabase]:
    """
    FastAPI dependency yielding the async MongoDB database.
    
    Usage:
        @router.get("/items")
        async def read_items(db: AsyncIOMotorDatabase = Depends(get_mongo_db)):
            ...
    """
    if _async_client is not None:
        settings = get_settings()
        return _async_client[settings.MONGODB_DB_NAME]
    return None


_last_sync_check_time = 0.0
_sync_is_available = True


def get_sync_mongo_db() -> Optional[SyncDatabase]:
    """
    Get a synchronous MongoDB database instance for background threads/workers.
    Falls back quickly if MongoDB is offline to prevent blocking delays.
    """
    global _sync_client, _last_sync_check_time, _sync_is_available
    import time
    settings = get_settings()
    now = time.time()

    if not _sync_is_available and (now - _last_sync_check_time < 15.0):
        return None

    try:
        if _sync_client is None:
            opts = _get_client_options(settings.MONGODB_URL, timeout_ms=1000)
            _sync_client = pymongo.MongoClient(
                settings.MONGODB_URL,
                maxPoolSize=20,
                **opts,
            )
        _sync_client.admin.command("ping")
        _sync_is_available = True
        return _sync_client[settings.MONGODB_DB_NAME]
    except Exception as exc:
        _last_sync_check_time = now
        _sync_is_available = False
        if _sync_client:
            try:
                _sync_client.close()
            except Exception:
                pass
            _sync_client = None
        logger.warning(f"Sync MongoDB connection unavailable ({exc}). Falling back to local storage.")
        return None
