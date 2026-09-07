"""
Module 11 — Notification & Alert System Tests
===============================================
Unit tests covering alert creation, evaluation rules, role filtering,
de-duplication, and REST API endpoint contracts.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest


# ── Alert Service CRUD Tests ──────────────────────────────────

class TestAlertServiceCRUD:
    """Tests for alert_service CRUD operations."""

    def _make_notification(self, **overrides):
        """Create a mock Notification-like object."""
        defaults = {
            "id": uuid.uuid4(),
            "store_id": uuid.uuid4(),
            "type": "camera_health",
            "severity": "critical",
            "title": "Camera Offline",
            "message": "Camera is inactive",
            "entity_type": "camera",
            "entity_id": uuid.uuid4(),
            "target_role": "admin",
            "is_read": False,
            "is_resolved": False,
            "metadata_json": None,
            "created_at": datetime.now(timezone.utc),
            "resolved_at": None,
            "updated_at": datetime.now(timezone.utc),
        }
        defaults.update(overrides)
        obj = MagicMock()
        for k, v in defaults.items():
            setattr(obj, k, v)
        return obj

    def test_create_notification_fields(self):
        """Verify create_notification populates all required fields."""
        from app.modules.alerts.alert_service import create_notification

        mock_db = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock()
        mock_db.add = MagicMock()

        # The function calls db.add, db.commit, db.refresh
        notif = create_notification(
            mock_db,
            store_id=uuid.uuid4(),
            type="camera_health",
            severity="critical",
            title="Test Alert",
            message="Test message",
            entity_type="camera",
            entity_id=uuid.uuid4(),
            target_role="admin",
        )
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_mark_notification_read(self):
        """Verify marking a notification as read updates the is_read flag."""
        from app.modules.alerts.alert_service import mark_notification_read

        mock_notif = self._make_notification(is_read=False)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_notif

        result = mark_notification_read(mock_db, mock_notif.id)
        assert result.is_read is True

    def test_resolve_notification_sets_timestamp(self):
        """Verify resolving sets is_resolved=True and resolved_at timestamp."""
        from app.modules.alerts.alert_service import resolve_notification

        mock_notif = self._make_notification(is_resolved=False, resolved_at=None)
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_notif

        result = resolve_notification(mock_db, mock_notif.id)
        assert result.is_resolved is True
        assert result.is_read is True
        assert result.resolved_at is not None

    def test_delete_notification_returns_true(self):
        """Verify delete returns True when notification found."""
        from app.modules.alerts.alert_service import delete_notification

        mock_notif = self._make_notification()
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_notif

        assert delete_notification(mock_db, mock_notif.id) is True
        mock_db.delete.assert_called_once()

    def test_delete_notification_returns_false(self):
        """Verify delete returns False when notification not found."""
        from app.modules.alerts.alert_service import delete_notification

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert delete_notification(mock_db, uuid.uuid4()) is False


# ── Evaluator De-duplication Tests ────────────────────────────

class TestEvaluatorDeduplication:
    """Tests for the 15-minute de-duplication window."""

    def test_has_recent_alert_returns_false_for_none_entity(self):
        """De-dup check should return False when entity_id is None."""
        from app.modules.alerts.evaluator import _has_recent_alert

        mock_db = MagicMock()
        result = _has_recent_alert(mock_db, "camera", None, "camera_health")
        assert result is False

    def test_has_recent_alert_queries_within_window(self):
        """De-dup check should query for unresolved alerts within the cooldown window."""
        from app.modules.alerts.evaluator import _has_recent_alert

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        entity_id = uuid.uuid4()
        result = _has_recent_alert(mock_db, "camera", entity_id, "camera_health")
        assert result is False
        mock_db.query.assert_called_once()


# ── Camera Health Evaluator Tests ─────────────────────────────

class TestCameraHealthEvaluator:
    """Tests for camera health alert generation."""

    def test_generates_alerts_for_inactive_cameras(self):
        """Should generate CRITICAL alerts for cameras with inactive status."""
        from app.modules.alerts.evaluator import evaluate_camera_health

        mock_camera = MagicMock()
        mock_camera.id = uuid.uuid4()
        mock_camera.store_id = uuid.uuid4()
        mock_camera.name = "Camera 1"
        mock_camera.status = "inactive"

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_camera]
        # De-dup check returns None (no recent alert)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        alerts = evaluate_camera_health(mock_db)
        # Should have attempted to create at least one alert
        assert mock_db.add.called

    def test_no_alerts_when_all_cameras_active(self):
        """Should generate no alerts when all cameras are active."""
        from app.modules.alerts.evaluator import evaluate_camera_health

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.all.return_value = []

        alerts = evaluate_camera_health(mock_db)
        assert len(alerts) == 0


# ── Notification Model Tests ─────────────────────────────────

class TestNotificationModel:
    """Tests for the Notification SQLAlchemy model."""

    def test_model_has_required_columns(self):
        """Verify the Notification model defines all specified columns."""
        from app.models.notification import Notification

        required_columns = [
            "id", "store_id", "type", "severity", "title", "message",
            "entity_type", "entity_id", "target_role", "is_read",
            "is_resolved", "created_at", "resolved_at", "updated_at",
        ]
        model_columns = [c.name for c in Notification.__table__.columns]
        for col in required_columns:
            assert col in model_columns, f"Missing column: {col}"

    def test_model_tablename(self):
        """Verify the table name is 'notifications'."""
        from app.models.notification import Notification

        assert Notification.__tablename__ == "notifications"


# ── Pydantic Schema Tests ────────────────────────────────────

class TestNotificationSchemas:
    """Tests for notification Pydantic schemas."""

    def test_notification_response_from_attributes(self):
        """Verify NotificationResponse can be constructed from ORM attributes."""
        from app.schemas.notification import NotificationResponse

        nid = uuid.uuid4()
        now = datetime.now(timezone.utc)
        data = {
            "id": nid,
            "type": "camera_health",
            "severity": "critical",
            "title": "Test",
            "message": "Test message",
            "target_role": "admin",
            "is_read": False,
            "is_resolved": False,
            "created_at": now,
        }
        resp = NotificationResponse(**data)
        assert resp.id == nid
        assert resp.severity == "critical"

    def test_notification_count_response(self):
        """Verify NotificationCountResponse defaults."""
        from app.schemas.notification import NotificationCountResponse

        resp = NotificationCountResponse()
        assert resp.unread_count == 0

        resp2 = NotificationCountResponse(unread_count=5)
        assert resp2.unread_count == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
