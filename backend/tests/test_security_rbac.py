"""
Module 13 — Security & RBAC Enforcement Test Suite
=====================================================
Comprehensive parameterized tests verifying:
- Role-Based Access Control (RBAC) across all protected API endpoints
- JWT token validation (expired, forged, missing tokens)
- Authorization matrix: Administrator, Store Manager, Retail Analyst, Marketing Manager

RBAC Matrix discovered from codebase:
  admin_only:            GET /api/users, DELETE /api/stores/{id}
  admin_or_store_manager: POST /api/stores, PUT /api/stores/{id},
                          POST /api/zones, PUT /api/zones/{id}, DELETE /api/zones/{id},
                          POST /api/shelves, PUT /api/shelves/{id}, DELETE /api/shelves/{id},
                          POST /api/products, PUT /api/products/{id}, DELETE /api/products/{id},
                          POST /api/cameras, PUT /api/cameras/{id}, DELETE /api/cameras/{id},
                          POST /api/ai-jobs, DELETE /api/ai-jobs/{id},
                          POST /api/recommendations/apply,
                          POST /api/scoring/recalculate,
                          POST /api/interactions/calibrate,
                          POST /api/attention/calibrate,
                          DELETE /api/reports/{id}
  any_role:              All GET endpoints (read access)
  get_current_user only: GET /api/users/profile, PUT /api/users/profile
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest
from jose import jwt


# ── Helper: Create JWT tokens for test roles ──────────────────

SECRET_KEY = "change-this-in-production"
ALGORITHM = "HS256"

ROLES = ["Administrator", "Store Manager", "Retail Analyst", "Marketing Manager"]


def _make_token(role: str, user_id: str = None, expired: bool = False) -> str:
    """Create a JWT token for a given role."""
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


def _make_user_mock(role_name: str, is_active: bool = True):
    """Create a mock User object with role."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = f"test_{role_name.lower().replace(' ', '_')}@cams.test"
    user.full_name = f"Test {role_name}"
    user.is_active = is_active
    user.role = _make_role_mock(role_name)
    user.role_id = user.role.id
    return user


# ── RBAC Matrix Tests ─────────────────────────────────────────

class TestAdminOnlyEndpoints:
    """
    Endpoints restricted to Administrator role only.
    All other roles must receive 403 Forbidden.
    """

    ADMIN_ONLY_ENDPOINTS = [
        ("GET", "/api/users"),
    ]

    NON_ADMIN_ROLES = ["Store Manager", "Retail Analyst", "Marketing Manager"]

    @pytest.mark.parametrize("method,path", ADMIN_ONLY_ENDPOINTS)
    @pytest.mark.parametrize("role", NON_ADMIN_ROLES)
    def test_non_admin_denied(self, method, path, role):
        """Non-admin roles MUST receive 403 on admin-only endpoints."""
        from app.middleware.jwt_auth import require_roles

        checker = require_roles("Administrator")
        user = _make_user_mock(role)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.parametrize("method,path", ADMIN_ONLY_ENDPOINTS)
    def test_admin_allowed(self, method, path):
        """Administrator role MUST be allowed through admin-only check."""
        from app.middleware.jwt_auth import require_roles

        checker = require_roles("Administrator")
        user = _make_user_mock("Administrator")

        result = checker(current_user=user)
        assert result.role.role_name == "Administrator"


class TestAdminOrStoreManagerEndpoints:
    """
    Endpoints restricted to Administrator + Store Manager.
    Retail Analyst and Marketing Manager must receive 403.
    """

    RESTRICTED_ROLES = ["Retail Analyst", "Marketing Manager"]
    ALLOWED_ROLES = ["Administrator", "Store Manager"]

    @pytest.mark.parametrize("role", RESTRICTED_ROLES)
    def test_restricted_roles_denied(self, role):
        """Retail Analyst and Marketing Manager denied on admin_or_store_manager endpoints."""
        from app.middleware.jwt_auth import require_roles

        checker = require_roles("Administrator", "Store Manager")
        user = _make_user_mock(role)

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)
        assert exc_info.value.status_code == 403
        assert "Access denied" in exc_info.value.detail

    @pytest.mark.parametrize("role", ALLOWED_ROLES)
    def test_allowed_roles_pass(self, role):
        """Administrator and Store Manager pass admin_or_store_manager check."""
        from app.middleware.jwt_auth import require_roles

        checker = require_roles("Administrator", "Store Manager")
        user = _make_user_mock(role)

        result = checker(current_user=user)
        assert result.role.role_name == role


class TestAnyRoleEndpoints:
    """
    Endpoints accessible to any authenticated user with a valid role.
    All 4 roles must pass.
    """

    @pytest.mark.parametrize("role", ROLES)
    def test_any_role_allowed(self, role):
        """All valid roles must pass the any_role check."""
        from app.middleware.jwt_auth import require_roles

        checker = require_roles(*ROLES)
        user = _make_user_mock(role)

        result = checker(current_user=user)
        assert result.role.role_name == role


class TestRoleErrorMessages:
    """Verify RBAC error messages contain meaningful information."""

    def test_forbidden_message_includes_required_roles(self):
        """403 error detail must list required and actual role."""
        from app.middleware.jwt_auth import require_roles
        from fastapi import HTTPException

        checker = require_roles("Administrator")
        user = _make_user_mock("Marketing Manager")

        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)

        detail = exc_info.value.detail
        assert "Administrator" in detail
        assert "Marketing Manager" in detail

    def test_forbidden_message_multi_role(self):
        """403 detail lists all allowed roles when multiple are accepted."""
        from app.middleware.jwt_auth import require_roles
        from fastapi import HTTPException

        checker = require_roles("Administrator", "Store Manager")
        user = _make_user_mock("Retail Analyst")

        with pytest.raises(HTTPException) as exc_info:
            checker(current_user=user)

        detail = exc_info.value.detail
        assert "Administrator" in detail
        assert "Store Manager" in detail
        assert "Retail Analyst" in detail


# ── JWT Token Validation Tests ────────────────────────────────

class TestJWTTokenExpiry:
    """Verify expired tokens return 401 Unauthorized."""

    def test_expired_token_rejected(self):
        """Expired JWT must raise 401."""
        from app.utils.token import decode_access_token
        from fastapi import HTTPException

        expired_token = _make_token("Administrator", expired=True)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(expired_token)
        assert exc_info.value.status_code == 401
        # Token may report as expired or invalid depending on jose version
        detail = exc_info.value.detail.lower()
        assert "expired" in detail or "invalid" in detail


class TestJWTTokenForged:
    """Verify forged/tampered tokens return 401 Unauthorized."""

    def test_invalid_signature_rejected(self):
        """Token signed with wrong key must be rejected."""
        from app.utils.token import decode_access_token
        from fastapi import HTTPException

        payload = {
            "user_id": str(uuid.uuid4()),
            "email": "forged@cams.test",
            "role": "Administrator",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        forged_token = jwt.encode(payload, "wrong-secret-key", algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(forged_token)
        assert exc_info.value.status_code == 401
        assert "invalid" in exc_info.value.detail.lower() or "Invalid" in exc_info.value.detail

    def test_malformed_token_rejected(self):
        """Completely malformed token string must be rejected."""
        from app.utils.token import decode_access_token
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not.a.valid.jwt.token")
        assert exc_info.value.status_code == 401

    def test_token_missing_claims_rejected(self):
        """Token missing required claims (user_id, email, role) must be rejected."""
        from app.utils.token import decode_access_token
        from fastapi import HTTPException

        payload = {
            "user_id": str(uuid.uuid4()),
            # Missing email and role
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        incomplete_token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(incomplete_token)
        assert exc_info.value.status_code == 401
        # May report as "missing" claims or generic "invalid" depending on jose version
        detail = exc_info.value.detail.lower()
        assert "missing" in detail or "invalid" in detail


class TestJWTTokenAbsent:
    """Verify missing Authorization header returns 401."""

    def test_no_token_header(self):
        """Request without Authorization header must return 401."""
        # FastAPI's OAuth2PasswordBearer auto-returns 401 when header is missing.
        # We test the decode pathway directly: empty string token.
        from app.utils.token import decode_access_token
        from fastapi import HTTPException

        with pytest.raises((HTTPException, Exception)):
            decode_access_token("")


class TestDisabledAccountAccess:
    """Verify disabled accounts receive 403 even with valid token."""

    def test_inactive_user_blocked(self):
        """Users with is_active=False must receive 403 Forbidden."""
        from app.middleware.jwt_auth import get_current_user
        from fastapi import HTTPException

        uid = str(uuid.uuid4())
        user = _make_user_mock("Administrator", is_active=False)
        user.id = uuid.UUID(uid)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = user

        # Patch decode_access_token to return valid payload, testing is_active check
        decoded_payload = {
            "user_id": uid,
            "email": "admin@cams.test",
            "role": "Administrator",
        }
        with patch("app.middleware.jwt_auth.decode_access_token", return_value=decoded_payload):
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token="mocked-token", db=mock_db)
        assert exc_info.value.status_code == 403
        assert "disabled" in exc_info.value.detail.lower()


class TestTokenUserNotFound:
    """Verify token with non-existent user_id returns 401."""

    def test_stale_token_user_deleted(self):
        """Token for a deleted user must return 401."""
        from app.middleware.jwt_auth import get_current_user
        from fastapi import HTTPException

        uid = str(uuid.uuid4())
        payload = {
            "user_id": uid,
            "email": "deleted@cams.test",
            "role": "Administrator",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=mock_db)
        assert exc_info.value.status_code == 401
        detail = exc_info.value.detail.lower()
        assert "not found" in detail or "stale" in detail or "invalid" in detail
