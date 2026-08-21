"""
FastAPI Application Entry Point
=================================
Configures CORS, includes route modules, and provides a health check.
This is the main file that Uvicorn loads to serve the application.

Run with:
    uvicorn app.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from app.api.module4 import router as module4_router
from app.api.module5 import router as module5_router

settings = get_settings()


# ── Lifespan (startup/shutdown events) ────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    # Startup
    print("[INFO] Consumer Attention Mapping System -- Backend Starting...")
    print(f"[INFO] CORS Origins: {settings.cors_origins_list}")
    print(f"[INFO] JWT Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
    google_status = "Configured" if settings.GOOGLE_CLIENT_ID else "Not configured"
    print(f"[INFO] Google OAuth: {google_status}")
    yield
    # Shutdown
    print("[INFO] Backend shutting down...")


# ── Application Instance ─────────────────────────────────────
app = FastAPI(
    title="Consumer Attention Mapping System",
    description=(
        "Module 1: Authentication & Role-Based Access Control. "
        "Module 2: Store & Shelf Management. "
        "Module 3: AI-Powered Consumer Tracking & Dwell Analysis. "
        "Module 4: Attention Analysis Engine (Gaze, Head Pose, Shelf & Product Engagement). "
        "Module 5: Product Interaction Analysis Module (Viewed, Pickup, Return, Comparison, Shelf Interaction). "
        "Provides user registration, login, JWT auth, Google OAuth, "
        "role-based permissions, full retail store management, "
        "and advanced shopper behavior & product interaction analytics."
    ),
    version="5.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
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

# Module 4: Attention Analysis Engine
app.include_router(module4_router)

# Module 5: Product Interaction Analysis Module
app.include_router(module5_router)


# ── Health Check ──────────────────────────────────────────────
@app.get(
    "/api/health",
    tags=["System"],
    summary="Health check",
)
def health_check():
    """Returns a simple health status for monitoring."""
    return {
        "status": "healthy",
        "service": "Consumer Attention Mapping System",
        "modules": [
            "Authentication & RBAC",
            "Store & Shelf Management",
            "AI Consumer Tracking & Dwell Analysis",
            "Attention Analysis Engine",
            "Product Interaction Analysis Module",
        ],
        "version": "5.0.0",
    }


