"""
Alert Service — CRUD Operations
=================================
Provides database query helpers for creating, listing, reading, resolving,
and deleting notifications.  Thread-safe, session-scoped operations.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.notification import Notification

logger = logging.getLogger("alert_service")


# ── Create ────────────────────────────────────────────────────

def create_notification(
    db: Session,
    *,
    store_id: uuid.UUID | None = None,
    type: str,
    severity: str = "info",
    title: str,
    message: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    target_role: str = "all",
    metadata: dict[str, Any] | None = None,
) -> Notification:
    """Insert a new notification row and return it."""
    notif = Notification(
        store_id=store_id,
        type=type,
        severity=severity,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        target_role=target_role,
        metadata_json=metadata,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    logger.info(f"Created notification {notif.id} [{severity}] {title}")
    return notif


# ── List / Query ──────────────────────────────────────────────

def list_notifications(
    db: Session,
    *,
    user_role: str = "all",
    store_id: uuid.UUID | None = None,
    severity: str | None = None,
    type_filter: str | None = None,
    is_read: bool | None = None,
    skip: int = 0,
    limit: int = 20,
) -> list[Notification]:
    """Return notifications visible to the given role, newest first."""
    query = db.query(Notification)

    # Role filtering: show alerts targeted to user's role OR to 'all'
    if user_role and user_role != "all":
        query = query.filter(
            Notification.target_role.in_([user_role, "all"])
        )

    if store_id:
        query = query.filter(Notification.store_id == store_id)
    if severity:
        query = query.filter(Notification.severity == severity)
    if type_filter:
        query = query.filter(Notification.type == type_filter)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    return (
        query.order_by(desc(Notification.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_unread_count(
    db: Session,
    *,
    user_role: str = "all",
    store_id: uuid.UUID | None = None,
) -> int:
    """Fast count of unread, unresolved notifications for the given role."""
    query = db.query(Notification).filter(
        Notification.is_read == False,  # noqa: E712
        Notification.is_resolved == False,  # noqa: E712
    )
    if user_role and user_role != "all":
        query = query.filter(Notification.target_role.in_([user_role, "all"]))
    if store_id:
        query = query.filter(Notification.store_id == store_id)
    return query.count()


def get_notification_by_id(
    db: Session, notification_id: uuid.UUID
) -> Notification | None:
    """Fetch a single notification by primary key."""
    return db.query(Notification).filter(Notification.id == notification_id).first()


# ── Mark Read ─────────────────────────────────────────────────

def mark_notification_read(
    db: Session, notification_id: uuid.UUID
) -> Notification | None:
    """Mark a single notification as read."""
    notif = get_notification_by_id(db, notification_id)
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif


def mark_all_read(
    db: Session,
    *,
    user_role: str = "all",
    store_id: uuid.UUID | None = None,
) -> int:
    """Mark all matching unread notifications as read.  Returns affected count."""
    query = db.query(Notification).filter(Notification.is_read == False)  # noqa: E712
    if user_role and user_role != "all":
        query = query.filter(Notification.target_role.in_([user_role, "all"]))
    if store_id:
        query = query.filter(Notification.store_id == store_id)

    count = query.update({Notification.is_read: True}, synchronize_session="fetch")
    db.commit()
    return count


# ── Resolve ───────────────────────────────────────────────────

def resolve_notification(
    db: Session, notification_id: uuid.UUID
) -> Notification | None:
    """Mark a notification as resolved with a timestamp."""
    notif = get_notification_by_id(db, notification_id)
    if notif:
        notif.is_resolved = True
        notif.is_read = True
        notif.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notif)
    return notif


# ── Delete ────────────────────────────────────────────────────

def delete_notification(
    db: Session, notification_id: uuid.UUID
) -> bool:
    """Hard-delete a notification.  Returns True if found and deleted."""
    notif = get_notification_by_id(db, notification_id)
    if notif:
        db.delete(notif)
        db.commit()
        return True
    return False
