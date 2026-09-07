"""
Alerts API
===========
REST endpoints for notification lifecycle management and
authenticated WebSocket endpoints for real-time alert streaming.
"""

import uuid
import logging

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.core.dependencies import any_role
from app.schemas.notification import (
    NotificationResponse,
    NotificationCountResponse,
    NotificationResolveRequest,
)
from app.modules.alerts import alert_service
from app.schemas.auth import MessageResponse

logger = logging.getLogger("alerts_api")

router = APIRouter(prefix="/api/alerts", tags=["Notifications & Alerts"])


# ── Helpers ───────────────────────────────────────────────────

def _get_user_role(current_user: User) -> str:
    """Extract role name from user object."""
    if hasattr(current_user, "role") and current_user.role:
        if hasattr(current_user.role, "role_name"):
            return current_user.role.role_name
        return str(current_user.role)
    return "all"


# ── REST Endpoints ────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[NotificationResponse],
    summary="List notifications for the current user's role",
)
def list_alerts(
    store_id: uuid.UUID | None = Query(None),
    severity: str | None = Query(None),
    type: str | None = Query(None),
    is_read: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Return notifications visible to the authenticated user's role."""
    role = _get_user_role(current_user)
    notifications = alert_service.list_notifications(
        db,
        user_role=role,
        store_id=store_id,
        severity=severity,
        type_filter=type,
        is_read=is_read,
        skip=skip,
        limit=limit,
    )
    return notifications


@router.get(
    "/unread-count",
    response_model=NotificationCountResponse,
    summary="Get unread notification count for the navbar badge",
)
def get_unread_count(
    store_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Fast unread count query for the notification bell badge."""
    role = _get_user_role(current_user)
    count = alert_service.get_unread_count(db, user_role=role, store_id=store_id)
    return NotificationCountResponse(unread_count=count)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark a single notification as read",
)
def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    notif = alert_service.mark_notification_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.post(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all notifications as read for the current user's role",
)
def mark_all_read(
    store_id: uuid.UUID | None = Query(None),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications as read for the user's role."""
    role = _get_user_role(current_user)
    count = alert_service.mark_all_read(db, user_role=role, store_id=store_id)
    return MessageResponse(message=f"Marked {count} notification(s) as read")


@router.post(
    "/{notification_id}/resolve",
    response_model=NotificationResponse,
    summary="Resolve an alert",
)
def resolve_alert(
    notification_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Mark a notification as resolved with a timestamp."""
    notif = alert_service.resolve_notification(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif


@router.delete(
    "/{notification_id}",
    response_model=MessageResponse,
    summary="Delete a notification",
)
def delete_alert(
    notification_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Hard-delete a notification."""
    deleted = alert_service.delete_notification(db, notification_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
    return MessageResponse(message="Notification deleted")


@router.post(
    "/evaluate",
    response_model=MessageResponse,
    summary="Manually trigger alert evaluation (diagnostic / testing)",
)
def trigger_evaluation(
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Run all alert evaluators immediately and return the count of new alerts."""
    from app.modules.alerts.evaluator import evaluate_periodic
    alerts = evaluate_periodic(db)
    return MessageResponse(message=f"Evaluation complete: {len(alerts)} new alert(s) generated")


# ── WebSocket Endpoint ────────────────────────────────────────

@router.websocket("/ws")
async def alert_websocket(websocket: WebSocket, token: str | None = None):
    """
    Authenticated WebSocket for real-time alert streaming.
    Connect with: ws://host/api/alerts/ws?token=<jwt>
    """
    from app.core.job_stream import job_stream_manager
    from app.utils.token import decode_access_token
    # pyrefly: ignore [missing-import]
    from fastapi import WebSocketDisconnect

    # Authenticate via JWT query param
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return

    try:
        payload = decode_access_token(token)
        role = payload.get("role", "all")
    except Exception:
        await websocket.close(code=4001, reason="Invalid authentication token")
        return

    await job_stream_manager.connect_alert_client(websocket, role=role)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        job_stream_manager.disconnect_alert_client(websocket)
    except Exception:
        job_stream_manager.disconnect_alert_client(websocket)
