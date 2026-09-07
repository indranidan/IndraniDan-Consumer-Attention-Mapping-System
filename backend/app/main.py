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
from app.api.recommendations import router as recommendations_router
from app.api.alerts import router as alerts_router
from app.api.reports import router as reports_router

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
    loop = asyncio.get_running_loop()
    job_stream_manager.set_event_loop(loop)

    from app.core.redis_listener import set_event_loop as set_bus_loop, start_redis_listener, stop_redis_listener
    from app.core.redis_client import is_redis_available
    set_bus_loop(loop)

    if is_redis_available():
        print("[INFO] Redis: Connected ✅ (Event bus: Redis Pub/Sub)")
    else:
        print("[INFO] Redis: Not available ⚠️ (Event bus: In-process fallback)")

    start_redis_listener()

    # Module 11: Start periodic alert evaluation background task
    async def _periodic_alert_evaluation():
        """60-second background loop for camera health and traffic anomaly checks."""
        import logging as _log
        _logger = _log.getLogger("alert_evaluator_bg")
        while True:
            try:
                await asyncio.sleep(60)
                from app.modules.alerts.evaluator import evaluate_periodic
                def _run_periodic():
                    with SessionLocal() as alert_db:
                        alerts = evaluate_periodic(alert_db)
                        if alerts:
                            _logger.info(f"Periodic evaluation: {len(alerts)} alert(s) generated")
                            from app.core.job_stream import job_stream_manager
                            for alert in alerts:
                                job_stream_manager.broadcast_alert_sync({
                                    "type": "ALERT_CREATED",
                                    "alert": {
                                        "id": str(alert.id),
                                        "severity": alert.severity,
                                        "title": alert.title,
                                        "message": alert.message,
                                        "alert_type": alert.type,
                                        "entity_type": alert.entity_type,
                                        "entity_id": str(alert.entity_id) if alert.entity_id else None,
                                        "target_role": alert.target_role,
                                    },
                                })
                await loop.run_in_executor(None, _run_periodic)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                _logger.warning(f"Periodic alert evaluation error: {exc}")
                await asyncio.sleep(10)

    _alert_bg_task = asyncio.create_task(_periodic_alert_evaluation())
    print("[INFO] Periodic alert evaluation started ✅ (60s interval)")

    yield

    # Shutdown
    print("[INFO] Backend shutting down...")
    _alert_bg_task.cancel()
    stop_redis_listener()
    await close_mongo()


# ── OpenAPI Tags Metadata ─────────────────────────────────────
OPENAPI_TAGS = [
    {
        "name": "Authentication",
        "description": "User registration, login, JWT token issuance, and Google OAuth2 integration.",
    },
    {
        "name": "Users",
        "description": "User account management, profile updates, and role-based access control (RBAC).",
    },
    {
        "name": "Stores",
        "description": "Retail store entity configuration, operational details, and store topology.",
    },
    {
        "name": "Zones",
        "description": "Store interior zones, department boundaries, and spatial region definitions.",
    },
    {
        "name": "Shelves",
        "description": "Shelf fixtures, coordinate placement, physical dimensions, and visual display management.",
    },
    {
        "name": "Products",
        "description": "Product catalog inventory, SKUs, category tagging, and pricing metadata.",
    },
    {
        "name": "Cameras",
        "description": "Camera devices, RTSP/video feeds, calibration zones, and optical coverage mapping.",
    },
    {
        "name": "Dashboard",
        "description": "Role-tailored retail intelligence KPIs, store health metrics, and executive summaries.",
    },
    {
        "name": "AI Analytics",
        "description": "AI computer vision jobs, video pipeline execution, webcam streaming, and job status.",
    },
    {
        "name": "Attention Analysis",
        "description": "3D head pose tracking, gaze fixation vectors, visual shelf engagement, and dwell metrics.",
    },
    {
        "name": "Product Interaction Analysis",
        "description": "Physical interaction detection: product views, pickups, returns, and comparative evaluations.",
    },
    {
        "name": "Consumer Behavior Intelligence",
        "description": "Shopper journey reconstruction, behavioral archetype segmentation, and Markov transition matrices.",
    },
    {
        "name": "Spatial Attention Heatmaps",
        "description": "Interactive Gaussian density heatmaps, shelf vertical attention profiles, and hotspot/dead-zone diagnostics.",
    },
    {
        "name": "Product Attractiveness Scoring",
        "description": "5-pillar Bayesian smoothed attractiveness scoring, relative conversion efficiency, and shelf visibility.",
    },
    {
        "name": "Recommendation & Optimization Engine",
        "description": "Prescriptive merchandising recommendations, automated shelf swaps, promotional placement, and what-if simulation.",
    },
    {
        "name": "Notifications & Alerts",
        "description": "Real-time alert dispatch, Redis Pub/Sub WebSocket feeds, camera offline alarms, and performance triggers.",
    },
    {
        "name": "Reports & Export System",
        "description": "Multi-domain PDF, Excel, CSV executive intelligence export engine, preview studio, and report ledger.",
    },
    {
        "name": "System",
        "description": "System liveness, database connectivity (PostgreSQL, MongoDB, Redis), and overall pipeline health.",
    },
]


# ── Application Instance ─────────────────────────────────────
app = FastAPI(
    title="Consumer Attention & Merchandising Intelligence Platform",
    description=(
        "## Enterprise AI Consumer Attention & Merchandising Optimization Platform\n\n"
        "Provides end-to-end computer vision processing, spatial attention tracking, and prescriptive retail merchandising intelligence across 12 core engines:\n\n"
        "- **Authentication & RBAC**: Multi-tenant authentication, JWT sessions, and Google OAuth2.\n"
        "- **Store & Fixture Management**: Retail store topology, zones, shelves, products, and camera optical mapping.\n"
        "- **Shopper Tracking & Dwell**: Edge and server video inference with real-time bounding box tracking and spatial dwell analysis.\n"
        "- **Gaze & Attention Engine**: 3D head pose estimation, gaze ray projection, and shelf fixation analytics.\n"
        "- **Product Interaction Engine**: Physical touch detection (views, pickups, returns, and comparisons).\n"
        "- **Behavioral Intelligence**: Shopper archetype clustering, journey path reconstruction, and Markov zone transition probabilities.\n"
        "- **Spatial Attention Heatmaps**: Interactive multi-layer Gaussian density heatmaps and vertical shelf engagement profiles.\n"
        "- **Product Attractiveness Scoring**: 5-pillar Bayesian smoothed product engagement index (0–100).\n"
        "- **Prescriptive Optimization**: Rule-based merchandising recommendations, layout improvements, and what-if simulator.\n"
        "- **Executive Dashboards**: Role-specific analytical views for Administrators, Store Managers, and Retail Analysts.\n"
        "- **Notification & Alert System**: Real-time event bus, Redis Pub/Sub, and WebSocket notification dispatch.\n"
        "- **Reports & Export System**: Automated multi-format reports (PDF, Excel XML, CSV) across all retail domains.\n"
        "- **Integration, Testing & Deployment**: End-to-end pipeline validation, RBAC security testing, deep health observability, and production deployment."
    ),
    version="13.0.0",
    openapi_tags=OPENAPI_TAGS,
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


# ── Security Headers Middleware ───────────────────────────────
# pyrefly: ignore [missing-import]
from starlette.middleware.base import BaseHTTPMiddleware
# pyrefly: ignore [missing-import]
from starlette.requests import Request as StarletteRequest


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach standard defensive HTTP security headers to every response."""

    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ── Routers ───────────────────────────────────────────────────
# Authentication & Identity Access Control
app.include_router(auth_router)
app.include_router(users_router)

# Store & Physical Fixture Topology
app.include_router(stores_router)
app.include_router(zones_router)
app.include_router(shelves_router)
app.include_router(products_router)
app.include_router(cameras_router)
app.include_router(dashboard_router)

# AI Computer Vision Pipeline & Tracking
app.include_router(ai_jobs_router)

# Gaze & Visual Attention Analysis Engine
app.include_router(attention_router)

# Physical Product Interaction Analysis Engine
app.include_router(interactions_router)

# Consumer Behavioral Intelligence Engine
app.include_router(behavior_router)

# Spatial Attention Heatmaps Engine
app.include_router(heatmaps_router)

# Product Attractiveness Scoring Engine
app.include_router(scoring_router)

# Prescriptive Merchandising & Optimization Engine
app.include_router(recommendations_router)

# Notification & Real-Time Alert System
app.include_router(alerts_router)

# Reports & Business Intelligence Export System
app.include_router(reports_router)


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

    # Check Redis
    from app.core.redis_client import is_redis_available
    redis_connected = is_redis_available()
    redis_status = "connected" if redis_connected else "disconnected"
    event_bus_mode = "redis_pubsub" if redis_connected else "in_process_fallback"

    google_configured = bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    overall_status = "healthy" if pg_status == "healthy" else "degraded"

    return {
        "status": overall_status,
        "service": "Consumer Attention Mapping System",
        "databases": {
            "postgresql": pg_status,
            "mongodb": mongo_status,
            "redis": redis_status,
        },
        "event_bus": {
            "mode": event_bus_mode,
            "redis_connected": redis_connected,
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
            "Recommendation & Optimization Engine",
            "Notification & Alert System",
            "Reports & Export System",
            "Integration, Testing & Deployment",
        ],
        "version": "13.0.0",
    }


# ── Deep Health Probe ─────────────────────────────────────────
@app.get(
    "/api/health/deep",
    tags=["System"],
    summary="Deep health probe",
    responses={
        200: {"description": "All subsystems healthy"},
        503: {"description": "One or more critical subsystems unavailable"},
    },
)
async def deep_health_check():
    """
    Comprehensive deep health probe for operational monitoring.

    Asynchronously probes all subsystems with 2-second timeouts:
    - PostgreSQL connection pool
    - MongoDB document store
    - Redis event bus and cache
    - Storage directory write permissions
    """
    import asyncio
    import time
    import tempfile

    from app.schemas.health import ComponentHealth, DeepHealthResponse
    from app.core.redis_client import get_redis_client

    components: dict[str, ComponentHealth] = {}
    critical_failure = False

    async def probe_postgresql():
        nonlocal critical_failure
        start = time.perf_counter()
        try:
            def _pg_ping():
                with SessionLocal() as db_session:
                    db_session.execute(text("SELECT 1"))
            loop = asyncio.get_running_loop()
            await asyncio.wait_for(loop.run_in_executor(None, _pg_ping), timeout=2.0)
            latency = (time.perf_counter() - start) * 1000
            components["postgresql"] = ComponentHealth(
                status="healthy", latency_ms=round(latency, 2),
                details="Connection pool active"
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            critical_failure = True
            components["postgresql"] = ComponentHealth(
                status="unavailable", latency_ms=round(latency, 2),
                details=str(exc)[:200]
            )

    async def probe_mongodb():
        nonlocal critical_failure
        start = time.perf_counter()
        try:
            client = get_mongo_client()
            if client is None:
                components["mongodb"] = ComponentHealth(
                    status="unavailable", latency_ms=0,
                    details="No MongoDB client available (fallback mode)"
                )
                critical_failure = True
                return
            await asyncio.wait_for(client.admin.command("ping"), timeout=2.0)
            latency = (time.perf_counter() - start) * 1000
            components["mongodb"] = ComponentHealth(
                status="healthy", latency_ms=round(latency, 2),
                details=f"Database: {settings.MONGODB_DB_NAME}"
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            critical_failure = True
            components["mongodb"] = ComponentHealth(
                status="unavailable", latency_ms=round(latency, 2),
                details=str(exc)[:200]
            )

    async def probe_redis():
        start = time.perf_counter()
        try:
            client = get_redis_client()
            if client is None:
                components["redis"] = ComponentHealth(
                    status="unavailable", latency_ms=0,
                    details="Redis client not connected"
                )
                return
            loop = asyncio.get_running_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, client.ping), timeout=2.0
            )
            latency = (time.perf_counter() - start) * 1000
            components["redis"] = ComponentHealth(
                status="healthy", latency_ms=round(latency, 2),
                details="Pub/Sub event bus active"
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            components["redis"] = ComponentHealth(
                status="degraded", latency_ms=round(latency, 2),
                details=str(exc)[:200]
            )

    async def probe_storage():
        start = time.perf_counter()
        try:
            storage_path = Path(settings.AI_OUTPUT_PATH)
            storage_path.mkdir(parents=True, exist_ok=True)
            test_file = storage_path / ".health_probe"
            loop = asyncio.get_running_loop()
            def _write_test():
                test_file.write_text("ok")
                test_file.unlink(missing_ok=True)
            await asyncio.wait_for(
                loop.run_in_executor(None, _write_test), timeout=2.0
            )
            latency = (time.perf_counter() - start) * 1000
            components["storage"] = ComponentHealth(
                status="healthy", latency_ms=round(latency, 2),
                details=f"Writable: {storage_path}"
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000
            components["storage"] = ComponentHealth(
                status="degraded", latency_ms=round(latency, 2),
                details=str(exc)[:200]
            )

    # Run all probes concurrently with individual 2-second timeouts
    await asyncio.gather(
        probe_postgresql(),
        probe_mongodb(),
        probe_redis(),
        probe_storage(),
    )

    # Determine overall status
    if critical_failure:
        overall = "critical"
    elif any(c.status == "degraded" for c in components.values()):
        overall = "degraded"
    else:
        overall = "healthy"

    response = DeepHealthResponse(
        overall_status=overall,
        components=components,
        modules_loaded=13,
        version="13.0.0",
    )

    from fastapi.responses import JSONResponse
    status_code = 200 if overall != "critical" else 503
    return JSONResponse(content=response.model_dump(), status_code=status_code)


