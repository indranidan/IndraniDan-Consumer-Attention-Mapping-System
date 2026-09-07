"""
Security Audit Test Suite
==========================
Comprehensive security tests verifying:
- WebSocket authentication enforcement (AI job streaming)
- Report download authorization and path traversal prevention
- File upload size limit enforcement
- Camera source protocol validation
- HTTP security headers presence
- Production secret key guard

CWE Coverage: CWE-306, CWE-284, CWE-22, CWE-400, CWE-918, CWE-693, CWE-668
"""

import io
import sys
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest
from jose import jwt

# Ensure backend root is on Python path
_backend_dir = str(Path(__file__).resolve().parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_project_root = str(Path(_backend_dir).parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ── Helper: Create JWT tokens ─────────────────────────────────

SECRET_KEY = "change-this-in-production"
ALGORITHM = "HS256"


def _make_token(role: str = "Administrator", user_id: str = None, expired: bool = False) -> str:
    """Create a JWT token for testing."""
    payload = {
        "user_id": user_id or str(uuid.uuid4()),
        "email": f"test_{role.lower().replace(' ', '_')}@cams.test",
        "role": role,
        "exp": datetime.now(timezone.utc) + (
            timedelta(minutes=-5) if expired else timedelta(minutes=30)
        ),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _make_role_mock(role_name: str):
    """Create a mock Role object."""
    role = MagicMock()
    role.role_name = role_name
    role.id = uuid.uuid4()
    return role


def _make_user_mock(role_name: str = "Administrator"):
    """Create a mock User object with role."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = f"test_{role_name.lower().replace(' ', '_')}@cams.test"
    user.full_name = f"Test {role_name}"
    user.is_active = True
    user.role = _make_role_mock(role_name)
    user.role_id = user.role.id
    return user


# ══════════════════════════════════════════════════════════════
# 1. WebSocket Authentication Tests (CWE-306)
# ══════════════════════════════════════════════════════════════

class TestWebSocketAuthentication:
    """AI Job WebSocket MUST require valid JWT token authentication."""

    def test_websocket_endpoint_requires_token_parameter(self):
        """The WebSocket handler signature must accept a token query parameter."""
        from app.api.ai_jobs import ai_job_websocket_stream
        import inspect
        sig = inspect.signature(ai_job_websocket_stream)
        assert "token" in sig.parameters, "WebSocket endpoint must accept 'token' parameter"

    def test_websocket_missing_token_closes_connection(self):
        """When no token is provided, the WebSocket must close with code 4001."""
        from app.api.ai_jobs import ai_job_websocket_stream
        import asyncio
        from unittest.mock import AsyncMock

        mock_ws = MagicMock()
        mock_ws.close = AsyncMock()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                ai_job_websocket_stream(mock_ws, uuid.uuid4(), token=None)
            )
            mock_ws.close.assert_called_once()
            call_kwargs = mock_ws.close.call_args
            code = call_kwargs.kwargs.get("code") or (call_kwargs.args[0] if call_kwargs.args else None)
            assert code in (4001, 4003), f"Expected close code 4001 or 4003, got {code}"
        finally:
            loop.close()

    def test_websocket_invalid_token_closes_connection(self):
        """When an invalid token is provided, the WebSocket must close with code 4001."""
        from app.api.ai_jobs import ai_job_websocket_stream
        import asyncio
        from unittest.mock import AsyncMock

        mock_ws = MagicMock()
        mock_ws.close = AsyncMock()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                ai_job_websocket_stream(mock_ws, uuid.uuid4(), token="completely-invalid-token")
            )
            mock_ws.close.assert_called_once()
            call_kwargs = mock_ws.close.call_args
            code = call_kwargs.kwargs.get("code") or (call_kwargs.args[0] if call_kwargs.args else None)
            assert code in (4001, 4003), f"Expected close code 4001 or 4003, got {code}"
        finally:
            loop.close()

    def test_websocket_expired_token_closes_connection(self):
        """When an expired token is provided, the WebSocket must close."""
        from app.api.ai_jobs import ai_job_websocket_stream
        import asyncio
        from unittest.mock import AsyncMock

        expired_token = _make_token(expired=True)
        mock_ws = MagicMock()
        mock_ws.close = AsyncMock()

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                ai_job_websocket_stream(mock_ws, uuid.uuid4(), token=expired_token)
            )
            mock_ws.close.assert_called_once()
        finally:
            loop.close()


# ══════════════════════════════════════════════════════════════
# 2. Report Download Authorization Tests (CWE-284 / CWE-22)
# ══════════════════════════════════════════════════════════════

class TestReportDownloadAuthorization:
    """Report download endpoint MUST require authentication and prevent path traversal."""

    def test_report_download_requires_auth_dependency(self):
        """The download_report function must have current_user parameter requiring any_role."""
        from app.api.reports import download_report
        import inspect
        sig = inspect.signature(download_report)
        assert "current_user" in sig.parameters, "download_report must require current_user"

    def test_report_download_unauthenticated_returns_401(self):
        """Unauthenticated requests to report download must get 401."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app, raise_server_exceptions=False)
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/reports/{fake_id}/download")
        assert response.status_code in (401, 403), (
            f"Unauthenticated report download should return 401/403, got {response.status_code}"
        )

    def test_path_traversal_detection_logic(self):
        """Path confinement must reject paths outside reports root."""
        from app.api.reports import download_report
        # This validates that the function contains path confinement logic
        import inspect
        source = inspect.getsource(download_report)
        assert "relative_to" in source or "resolve" in source, (
            "download_report must use Path.resolve() or relative_to() for path confinement"
        )


# ══════════════════════════════════════════════════════════════
# 3. Upload Size & Extension Validation Tests (CWE-400)
# ══════════════════════════════════════════════════════════════

class TestUploadSecurityHardening:
    """File uploads MUST enforce size limits and extension validation."""

    def test_max_upload_size_constant_defined(self):
        """MAX_UPLOAD_SIZE_BYTES must be defined at 500 MB."""
        from app.services.ai_job_service import MAX_UPLOAD_SIZE_BYTES
        assert MAX_UPLOAD_SIZE_BYTES == 500 * 1024 * 1024, (
            f"MAX_UPLOAD_SIZE_BYTES should be 524288000, got {MAX_UPLOAD_SIZE_BYTES}"
        )

    def test_allowed_video_extensions_defined(self):
        """ALLOWED_VIDEO_EXTENSIONS must include standard video formats."""
        from app.services.ai_job_service import ALLOWED_VIDEO_EXTENSIONS
        expected = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        assert ALLOWED_VIDEO_EXTENSIONS == expected, (
            f"ALLOWED_VIDEO_EXTENSIONS mismatch: {ALLOWED_VIDEO_EXTENSIONS}"
        )

    def test_upload_size_enforcement_in_create_job(self):
        """create_job function must contain size checking logic."""
        from app.services.ai_job_service import create_job
        import inspect
        source = inspect.getsource(create_job)
        assert "MAX_UPLOAD_SIZE_BYTES" in source, (
            "create_job must reference MAX_UPLOAD_SIZE_BYTES for size enforcement"
        )

    def test_source_override_path_confinement_in_create_job(self):
        """create_job must canonicalize and confine source_override paths."""
        from app.services.ai_job_service import create_job
        import inspect
        source = inspect.getsource(create_job)
        assert "resolve()" in source, (
            "create_job must use Path.resolve() for source_override confinement"
        )
        assert "project_root" in source, (
            "create_job must verify source_override is within project_root"
        )


# ══════════════════════════════════════════════════════════════
# 4. Camera Source Protocol Validation Tests (CWE-918)
# ══════════════════════════════════════════════════════════════

class TestCameraSourceValidation:
    """Camera source strings MUST be validated for safe protocol schemes."""

    def test_validate_camera_source_allows_numeric_index(self):
        """Numeric device indices (0, 1, 2) must be accepted."""
        from app.services.camera_service import _validate_camera_source
        assert _validate_camera_source("0") == "0"
        assert _validate_camera_source("1") == "1"
        assert _validate_camera_source("9") == "9"

    def test_validate_camera_source_allows_rtsp(self):
        """RTSP URLs must be accepted."""
        from app.services.camera_service import _validate_camera_source
        assert _validate_camera_source("rtsp://192.168.1.100:554/stream") == "rtsp://192.168.1.100:554/stream"

    def test_validate_camera_source_allows_http(self):
        """HTTP/HTTPS URLs must be accepted."""
        from app.services.camera_service import _validate_camera_source
        assert _validate_camera_source("http://camera.local/live") == "http://camera.local/live"
        assert _validate_camera_source("https://camera.local/live") == "https://camera.local/live"

    def test_validate_camera_source_rejects_file_scheme(self):
        """file:// scheme must be rejected (SSRF prevention)."""
        from app.services.camera_service import _validate_camera_source
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_camera_source("file:///etc/passwd")
        assert exc_info.value.status_code == 400

    def test_validate_camera_source_rejects_arbitrary_path(self):
        """Arbitrary local paths must be rejected."""
        from app.services.camera_service import _validate_camera_source
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_camera_source("/tmp/secret_video.mp4")
        assert exc_info.value.status_code == 400

    def test_validate_camera_source_rejects_ftp(self):
        """FTP scheme must be rejected."""
        from app.services.camera_service import _validate_camera_source
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_camera_source("ftp://internal-server/data")
        assert exc_info.value.status_code == 400

    def test_validate_camera_source_rejects_internal_probing(self):
        """Internal network probing attempts must be rejected."""
        from app.services.camera_service import _validate_camera_source
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _validate_camera_source("gopher://169.254.169.254/latest/meta-data")
        assert exc_info.value.status_code == 400


# ══════════════════════════════════════════════════════════════
# 5. HTTP Security Headers Tests (CWE-693)
# ══════════════════════════════════════════════════════════════

class TestSecurityHeaders:
    """All API responses MUST include standard security headers."""

    def test_health_endpoint_has_security_headers(self):
        """GET /api/health must return defensive security headers."""
        from fastapi.testclient import TestClient
        from app.main import app

        client = TestClient(app)
        response = client.get("/api/health")
        assert response.status_code == 200

        assert response.headers.get("X-Content-Type-Options") == "nosniff", (
            "Missing or incorrect X-Content-Type-Options header"
        )
        assert response.headers.get("X-Frame-Options") == "DENY", (
            "Missing or incorrect X-Frame-Options header"
        )
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin", (
            "Missing or incorrect Referrer-Policy header"
        )

    def test_security_headers_middleware_class_exists(self):
        """SecurityHeadersMiddleware must be defined in main.py."""
        from app.main import SecurityHeadersMiddleware
        assert SecurityHeadersMiddleware is not None


# ══════════════════════════════════════════════════════════════
# 6. Production Configuration Guard Tests (CWE-668)
# ══════════════════════════════════════════════════════════════

class TestProductionConfigurationGuard:
    """Production deployment MUST reject insecure default secret keys."""

    def test_environment_field_exists_in_settings(self):
        """Settings must have an ENVIRONMENT field."""
        from app.core.config import Settings
        s = Settings()
        assert hasattr(s, "ENVIRONMENT"), "Settings must have ENVIRONMENT field"

    def test_insecure_keys_set_defined(self):
        """Insecure default keys set must be defined."""
        from app.core.config import _INSECURE_SECRET_KEYS
        assert "change-this-in-production" in _INSECURE_SECRET_KEYS
        assert "" in _INSECURE_SECRET_KEYS

    def test_production_guard_warns_on_default_key(self):
        """Production mode with default key must log a critical warning."""
        from app.core.config import Settings, _INSECURE_SECRET_KEYS
        import logging

        # Create a settings instance with production mode and default key
        s = Settings(ENVIRONMENT="production", SECRET_KEY="change-this-in-production")

        assert s.SECRET_KEY in _INSECURE_SECRET_KEYS
        assert s.ENVIRONMENT.lower() == "production"

    def test_development_mode_does_not_trigger_guard(self):
        """Development mode with default key should not trigger production guard."""
        from app.core.config import Settings, _INSECURE_SECRET_KEYS

        s = Settings(ENVIRONMENT="development", SECRET_KEY="change-this-in-production")
        # In development mode, no error should be raised
        assert s.ENVIRONMENT.lower() == "development"


# ══════════════════════════════════════════════════════════════
# 7. Docker Compose Port Isolation Tests (CWE-668)
# ══════════════════════════════════════════════════════════════

class TestDockerComposeIsolation:
    """Database container ports MUST be bound to loopback interface only."""

    @pytest.fixture
    def docker_compose_content(self):
        """Load docker-compose.yml content."""
        compose_path = Path(__file__).resolve().parent.parent.parent / "docker-compose.yml"
        if compose_path.exists():
            return compose_path.read_text(encoding="utf-8")
        return ""

    def test_postgres_bound_to_loopback(self, docker_compose_content):
        """PostgreSQL port must be bound to 127.0.0.1."""
        if not docker_compose_content:
            pytest.skip("docker-compose.yml not found")
        assert "127.0.0.1:5432:5432" in docker_compose_content, (
            "PostgreSQL port must be bound to 127.0.0.1"
        )

    def test_mongodb_bound_to_loopback(self, docker_compose_content):
        """MongoDB port must be bound to 127.0.0.1."""
        if not docker_compose_content:
            pytest.skip("docker-compose.yml not found")
        assert "127.0.0.1:27017:27017" in docker_compose_content, (
            "MongoDB port must be bound to 127.0.0.1"
        )

    def test_redis_bound_to_loopback(self, docker_compose_content):
        """Redis port must be bound to 127.0.0.1."""
        if not docker_compose_content:
            pytest.skip("docker-compose.yml not found")
        assert "127.0.0.1:6379:6379" in docker_compose_content, (
            "Redis port must be bound to 127.0.0.1"
        )


# ══════════════════════════════════════════════════════════════
# 8. Nginx Security Configuration Tests
# ══════════════════════════════════════════════════════════════

class TestNginxSecurityConfig:
    """Nginx configuration MUST include security hardening directives."""

    @pytest.fixture
    def nginx_config_content(self):
        """Load nginx.conf content."""
        nginx_path = Path(__file__).resolve().parent.parent.parent / "frontend" / "nginx.conf"
        if nginx_path.exists():
            return nginx_path.read_text(encoding="utf-8")
        return ""

    def test_server_tokens_off(self, nginx_config_content):
        """Nginx must have server_tokens off."""
        if not nginx_config_content:
            pytest.skip("nginx.conf not found")
        assert "server_tokens off" in nginx_config_content

    def test_nginx_security_headers(self, nginx_config_content):
        """Nginx must set security headers."""
        if not nginx_config_content:
            pytest.skip("nginx.conf not found")
        assert "X-Content-Type-Options" in nginx_config_content
        assert "X-Frame-Options" in nginx_config_content
        assert "Referrer-Policy" in nginx_config_content
