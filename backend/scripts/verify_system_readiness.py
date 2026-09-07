"""
CAMS Production Deployment Readiness & Pre-Flight Verification Probe
====================================================================
Validates all system infrastructure components prior to production deployment:
1. Environment configuration & cryptographic secret strength
2. PostgreSQL connection pool & relational schema table integrity
3. MongoDB connection & analytical document collection availability
4. Redis event bus & cache readiness (with graceful in-memory fallback check)
5. Filesystem storage directory existence & read/write permissions
6. FastAPI route registration across all 13 retail intelligence modules

Usage:
    python scripts/verify_system_readiness.py [--strict] [--json-out readiness.json]
"""

import argparse
import json
import logging
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure backend root and project root are on Python path
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))
_project_root = _backend_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sqlalchemy import inspect, text
from app.core.config import get_settings
from app.database.database import SessionLocal, engine
from app.database.mongodb import get_sync_mongo_db, is_mongo_available
from app.core.redis_client import is_redis_available, get_redis_client
from app.main import app

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("readiness")


class SystemReadinessVerifier:
    """Performs deep pre-flight health, configuration, and connectivity verification."""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.settings = get_settings()
        env_name = getattr(self.settings, "ENVIRONMENT", os.environ.get("ENVIRONMENT", "development"))
        self.report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": env_name,
            "checks": {},
            "verdict": "UNKNOWN",
        }

    def check_environment_and_secrets(self) -> Dict[str, Any]:
        """Verify environment variable loading and security thresholds."""
        issues = []
        warnings = []

        secret = self.settings.SECRET_KEY
        if not secret or len(secret) < 32:
            issues.append("SECRET_KEY must be at least 32 characters long for cryptographic security.")
        if "default" in secret.lower() or "secret" in secret.lower() or "changeme" in secret.lower():
            warnings.append("SECRET_KEY appears to use a default or generic pattern. Replace for production.")

        env_name = getattr(self.settings, "ENVIRONMENT", os.environ.get("ENVIRONMENT", "development"))
        status = "FAIL" if issues else ("WARN" if warnings else "OK")
        return {
            "name": "Environment & Security Configuration",
            "status": status,
            "details": {
                "environment": env_name,
                "algorithm": self.settings.ALGORITHM,
                "token_expire_minutes": self.settings.ACCESS_TOKEN_EXPIRE_MINUTES,
                "cors_origins_count": len(self.settings.cors_origins_list),
            },
            "issues": issues,
            "warnings": warnings,
        }

    def check_postgresql_database(self) -> Dict[str, Any]:
        """Validate PostgreSQL connection pool and expected relational tables."""
        issues = []
        warnings = []
        table_count = 0
        latency_ms = 0.0

        required_tables = {
            "stores", "zones", "cameras", "shelves", "products",
            "users", "roles", "notifications", "ai_jobs"
        }

        try:
            t0 = time.perf_counter()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                inspector = inspect(conn)
                tables = set(inspector.get_table_names())
                table_count = len(tables)
                missing = required_tables - tables
                if missing:
                    warnings.append(f"Missing recommended relational tables: {', '.join(sorted(missing))}")
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        except Exception as exc:
            issues.append(f"Database connection failed: {exc}")

        status = "FAIL" if issues else ("WARN" if warnings else "OK")
        return {
            "name": "PostgreSQL Relational Storage",
            "status": status,
            "details": {
                "latency_ms": latency_ms,
                "total_tables": table_count,
                "driver": engine.driver,
            },
            "issues": issues,
            "warnings": warnings,
        }

    def check_mongodb_document_store(self) -> Dict[str, Any]:
        """Verify MongoDB document store and analytical collections."""
        issues = []
        warnings = []
        latency_ms = 0.0
        collections = []

        try:
            t0 = time.perf_counter()
            if is_mongo_available():
                db = get_sync_mongo_db()
                if db is not None:
                    collections = db.list_collection_names()
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            else:
                warnings.append("MongoDB unreachable. CAMS will utilize local JSON disk fallbacks for M3/M4/M6 artifacts.")
        except Exception as exc:
            warnings.append(f"MongoDB check error: {exc}")

        status = "FAIL" if issues else ("WARN" if warnings else "OK")
        return {
            "name": "MongoDB Analytical Document Store",
            "status": status,
            "details": {
                "connected": is_mongo_available(),
                "latency_ms": latency_ms,
                "collections": collections,
            },
            "issues": issues,
            "warnings": warnings,
        }

    def check_redis_cache_and_event_bus(self) -> Dict[str, Any]:
        """Verify Redis Pub/Sub event bus and cache connectivity."""
        warnings = []
        latency_ms = 0.0

        try:
            t0 = time.perf_counter()
            if is_redis_available():
                client = get_redis_client()
                client.ping()
                latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            else:
                warnings.append("Redis server offline. CAMS will utilize in-process async event dispatching.")
        except Exception as exc:
            warnings.append(f"Redis ping failed: {exc}")

        status = "WARN" if warnings else "OK"
        return {
            "name": "Redis Cache & Pub/Sub Event Bus",
            "status": status,
            "details": {
                "connected": is_redis_available(),
                "latency_ms": latency_ms,
                "fallback_active": not is_redis_available(),
            },
            "issues": [],
            "warnings": warnings,
        }

    def check_filesystem_storage_permissions(self) -> Dict[str, Any]:
        """Verify storage directories exist with read and write permissions."""
        issues = []
        warnings = []
        verified_dirs = []

        target_dirs = [
            _project_root / "storage",
            _project_root / "storage" / "reports",
            _project_root / "outputs",
            _project_root / "outputs" / "ai_jobs",
        ]

        for d in target_dirs:
            try:
                d.mkdir(parents=True, exist_ok=True)
                test_file = d / f".probe_{uuid.uuid4().hex[:6]}.tmp"
                test_file.write_text("cams_write_test", encoding="utf-8")
                assert test_file.read_text(encoding="utf-8") == "cams_write_test"
                test_file.unlink()
                verified_dirs.append(str(d.relative_to(_project_root)))
            except Exception as exc:
                issues.append(f"Directory {d} lacks read/write permissions: {exc}")

        status = "FAIL" if issues else "OK"
        return {
            "name": "Filesystem Storage Permissions",
            "status": status,
            "details": {
                "verified_directories": verified_dirs,
            },
            "issues": issues,
            "warnings": warnings,
        }

    def check_api_route_registration(self) -> Dict[str, Any]:
        """Verify that all required Module 1-13 API route groups are registered."""
        issues = []
        warnings = []

        expected_prefixes = [
            "/api/auth",
            "/api/users",
            "/api/stores",
            "/api/cameras",
            "/api/zones",
            "/api/shelves",
            "/api/products",
            "/api/ai",
            "/api/v1/attention",
            "/api/v1/interactions",
            "/api/behavior",
            "/api/v1/scoring",
            "/api/v1/recommendations",
            "/api/alerts",
            "/api/reports",
            "/api/heatmaps",
            "/api/dashboard",
            "/api/health",
            "/api/health/deep",
        ]

        registered_paths = [getattr(r, "path", "") for r in app.routes]
        missing_prefixes = []
        for prefix in expected_prefixes:
            if not any(p == prefix or p.startswith(prefix + "/") for p in registered_paths):
                missing_prefixes.append(prefix)

        if missing_prefixes:
            issues.append(f"Missing API route endpoints: {', '.join(missing_prefixes)}")

        status = "FAIL" if issues else "OK"
        return {
            "name": "FastAPI Route Group Registration",
            "status": status,
            "details": {
                "total_routes_registered": len(app.routes),
                "expected_prefixes_checked": len(expected_prefixes),
            },
            "issues": issues,
            "warnings": warnings,
        }

    def run_all_checks(self) -> Dict[str, Any]:
        """Execute all readiness probes and compute overall deployment readiness."""
        logger.info("\n" + "=" * 75)
        logger.info("   CAMS PRODUCTION DEPLOYMENT READINESS PROBE")
        logger.info("=" * 75 + "\n")

        checks = {
            "environment": self.check_environment_and_secrets(),
            "database": self.check_postgresql_database(),
            "mongodb": self.check_mongodb_document_store(),
            "redis": self.check_redis_cache_and_event_bus(),
            "storage": self.check_filesystem_storage_permissions(),
            "routes": self.check_api_route_registration(),
        }
        self.report["checks"] = checks

        has_fail = any(c["status"] == "FAIL" for c in checks.values())
        has_warn = any(c["status"] == "WARN" for c in checks.values())

        if has_fail:
            verdict = "NOT_READY"
        elif has_warn and self.strict:
            verdict = "NOT_READY (STRICT)"
        elif has_warn:
            verdict = "READY_WITH_WARNINGS"
        else:
            verdict = "READY"

        self.report["verdict"] = verdict
        self._print_results(checks, verdict)
        return self.report

    def _print_results(self, checks: Dict[str, Any], verdict: str) -> None:
        """Format probe output into an operator summary."""
        logger.info(f"{'Readiness Subsystem Probe':<45} | {'Status':<10} | {'Observations'}")
        logger.info("-" * 75)

        for check in checks.values():
            name = check["name"]
            st = check["status"]
            badge = f"[ {st} ]"
            notes = ""
            if check["issues"]:
                notes = check["issues"][0]
            elif check["warnings"]:
                notes = check["warnings"][0]
            else:
                notes = "All assertions validated"
            if len(notes) > 40:
                notes = notes[:37] + "..."
            logger.info(f"{name:<45} | {badge:<10} | {notes}")

        logger.info("-" * 75)
        logger.info(f"\nFinal Readiness Verdict: {verdict}\n")


def main():
    parser = argparse.ArgumentParser(description="CAMS System Readiness Probe")
    parser.add_argument("--strict", action="store_true", help="Fail if any warnings are detected")
    parser.add_argument("--json-out", type=str, default=None, help="Save structured JSON readiness report")
    args = parser.parse_args()

    verifier = SystemReadinessVerifier(strict=args.strict)
    report = verifier.run_all_checks()

    if args.json_out:
        p = Path(args.json_out)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Readiness report saved to {p}")

    is_ready = report["verdict"] in ("READY", "READY_WITH_WARNINGS")
    sys.exit(0 if is_ready else 1)


if __name__ == "__main__":
    main()
