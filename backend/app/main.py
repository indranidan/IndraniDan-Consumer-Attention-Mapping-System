"""
FastAPI Application Entry Point
=================================
Configures CORS, includes route modules, and provides a health check.
This is the main file that Uvicorn loads to serve the application.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# pyrefly: ignore [missing-import]
from fastapi import FastAPI
# pyrefly: ignore [missing-import]
from fastapi.middleware.cors import CORSMiddleware
# pyrefly: ignore [missing-import]
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import get_settings
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.stores import router as stores_router
from app.api.zones import router as zones_router
from app.api.shelves import router as shelves_router
from app.api.products import router as products_router
from app.api.cameras import router as cameras_router
from app.api.dashboard import router as dashboard_router
from app.api.ai_jobs import router as ai_jobs_router
from app.api.attention import router as attention_router
from app.api.interactions import router as interactions_router
from app.api.behavior import router as behavior_router
from app.api.heatmaps import router as heatmaps_router
from app.api.scoring import router as scoring_router

from app.database.database import SessionLocal
from app.database.mongodb import connect_mongo, close_mongo, get_mongo_client
# pyrefly: ignore [missing-import]
from sqlalchemy import text

# Ensure UTF-8 output encoding on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

settings = get_settings()


# ── Lifespan (startup/shutdown events) ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print("[INFO] Consumer Attention Mapping System -- Backend Starting...")
    print(f"[INFO] CORS Origins: {settings.cors_origins_list}")
    print(f"[INFO] JWT Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")

    # PostgreSQL status check
    try:
        with SessionLocal() as db_session:
            db_session.execute(text("SELECT 1"))
            # Safety schema check for zone_config column
            db_session.execute(text("ALTER TABLE ai_jobs ADD COLUMN IF NOT EXISTS zone_config JSON;"))
            db_session.commit()
        db_target = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "Active"
        print(f"[INFO] PostgreSQL: Connected ✅ ({db_target})")
    except Exception as exc:
        print(f"[WARNING] PostgreSQL: Connection check failed ❌ ({exc})")

    # MongoDB status check & connection
    mongo_client = await connect_mongo()
    if mongo_client:
        print(f"[INFO] MongoDB: Connected ✅ (Database: {settings.MONGODB_DB_NAME})")
    else:
        print(f"[INFO] MongoDB: Fallback Mode ❌ (Local storage active)")

    # Google OAuth status check
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        cid_preview = settings.GOOGLE_CLIENT_ID[:12] + "..." if len(settings.GOOGLE_CLIENT_ID) > 15 else settings.GOOGLE_CLIENT_ID
        print(f"[INFO] Google OAuth: Configured ✅ (Client ID: {cid_preview})")
    else:
        print("[INFO] Google OAuth: Not configured ❌")

    import asyncio
    from app.core.job_stream import job_stream_manager
    job_stream_manager.set_event_loop(asyncio.get_running_loop())

    yield

    # Shutdown
    print("[INFO] Backend shutting down...")
    await close_mongo()


# ── Application Instance ─────────────────────────────────────
app = FastAPI(
    title="Consumer Attention Mapping System",
    description=(
        "Module 1: Authentication & Role-Based Access Control. "
        "Module 2: Store & Shelf Management. "
        "Module 3: AI-Powered Consumer Tracking & Dwell Analysis. "
        "Module 4: Attention Analysis Engine (Gaze, Head Pose, Shelf & Product Engagement). "
        "Module 5: Product Interaction Analysis Module (Viewed, Pickup, Return, Comparison, Shelf Interaction). "
        "Module 6: Consumer Behavior Intelligence Engine (Shopper Segmentation, Journeys, Transitions). "
        "Module 8: Product Attractiveness Scoring Engine (5-Pillar Scoring, Bayesian Smoothing, Shelf Visibility). "
        "Provides user registration, login, JWT auth, Google OAuth, "
        "role-based permissions, full retail store management, "
        "and advanced shopper behavior & product interaction analytics."
    ),
    version="8.0.0",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────
# Session middleware is required for Google OAuth state management.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
)

# CORS — allow the frontend to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["x-total-count", "X-Total-Count"],
)


# ── Routers ───────────────────────────────────────────────────
# Module 1: Authentication & RBAC
app.include_router(auth_router)
app.include_router(users_router)

# Module 2: Store & Shelf Management
app.include_router(stores_router)
app.include_router(zones_router)
app.include_router(shelves_router)
app.include_router(products_router)
app.include_router(cameras_router)
app.include_router(dashboard_router)

# Module 3: AI Analytics
app.include_router(ai_jobs_router)

# Attention Analysis Engine
app.include_router(attention_router)

# Product Interaction Analysis Module
app.include_router(interactions_router)

# Consumer Behavior Intelligence Engine
app.include_router(behavior_router)

# Module 7: Attention Heatmap Engine
app.include_router(heatmaps_router)

# Module 8: Product Attractiveness Scoring Engine
app.include_router(scoring_router)


# ── Health Check ──────────────────────────────────────────────
@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check",
)
def health_check():
    """Returns system and database health status for monitoring."""
    # Check PostgreSQL
    pg_status = "healthy"
    try:
        with SessionLocal() as db_session:
            db_session.execute(text("SELECT 1"))
    except Exception as exc:
        pg_status = f"unhealthy: {str(exc)}"

    # Check MongoDB
    mongo_client = get_mongo_client()
    mongo_status = "connected" if mongo_client is not None else "fallback_mode"

    google_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    overall_status = "healthy" if pg_status == "healthy" else "degraded"

    return {
        "status": overall_status,
        "service": "Consumer Attention Mapping System",
        "databases": {
            "postgresql": pg_status,
            "mongodb": mongo_status,
        },
        "auth_providers": {
            "password": True,
            "google_oauth": google_configured,
        },
        "modules": [
            "Authentication & RBAC",
            "Store & Shelf Management",
            "AI Consumer Tracking & Dwell Analysis",
            "Attention Analysis Engine",
            "Product Interaction Analysis Module",
            "Consumer Behavior Intelligence Engine",
            "Attention Heatmap Engine",
            "Product Attractiveness Scoring Engine",
        ],
        "version": "8.0.0",
    }


