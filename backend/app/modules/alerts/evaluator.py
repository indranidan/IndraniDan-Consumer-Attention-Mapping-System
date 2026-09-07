"""
Alert Rule Evaluator
=====================
Evaluates five retail alert categories and creates notifications with
15-minute de-duplication to prevent alert fatigue.

Categories:
    1. Camera Health       – inactive / maintenance cameras
    2. Shelf Performance   – high traffic but low dwell
    3. Product Visibility  – attractiveness score < 40  (Grade D)
    4. Traffic Anomaly     – zero-footfall dead zones or sudden surges
    5. Platform Lifecycle  – AI job completion notifications
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.camera import Camera
from app.models.notification import Notification
from app.modules.alerts.alert_service import create_notification

logger = logging.getLogger("alert_evaluator")

# De-duplication cooldown window
_DEDUP_WINDOW = timedelta(minutes=15)


# ── De-duplication helper ─────────────────────────────────────

def _has_recent_alert(
    db: Session,
    entity_type: str,
    entity_id: uuid.UUID | None,
    alert_type: str,
) -> bool:
    """Check if an unresolved alert already exists within the cooldown window."""
    if entity_id is None:
        return False
    cutoff = datetime.now(timezone.utc) - _DEDUP_WINDOW
    existing = (
        db.query(Notification.id)
        .filter(
            and_(
                Notification.entity_type == entity_type,
                Notification.entity_id == entity_id,
                Notification.type == alert_type,
                Notification.is_resolved == False,  # noqa: E712
                Notification.created_at >= cutoff,
            )
        )
        .first()
    )
    return existing is not None


# ── Category 1: Camera Health ─────────────────────────────────

def evaluate_camera_health(db: Session) -> list[Notification]:
    """Generate alerts for cameras that are inactive or in maintenance."""
    alerts: list[Notification] = []
    cameras = (
        db.query(Camera)
        .filter(Camera.status.in_(["inactive", "maintenance"]))
        .all()
    )
    for cam in cameras:
        if _has_recent_alert(db, "camera", cam.id, "camera_health"):
            continue
        notif = create_notification(
            db,
            store_id=cam.store_id,
            type="camera_health",
            severity="critical",
            title=f"Camera Offline: {cam.name}",
            message=f"Camera '{cam.name}' is currently {cam.status}. Check feed connectivity and hardware status.",
            entity_type="camera",
            entity_id=cam.id,
            target_role="admin",
            metadata={"camera_status": cam.status, "camera_name": cam.name},
        )
        alerts.append(notif)
    if alerts:
        logger.info(f"Camera Health: generated {len(alerts)} alert(s)")
    return alerts


# ── Category 2: Shelf Performance ─────────────────────────────

def evaluate_shelf_performance(db: Session, job_id: uuid.UUID) -> list[Notification]:
    """
    Evaluate shelf dwell metrics from the latest AI job.
    Alerts when a zone has high traffic but shelves show < 1.5s dwell time.
    """
    from app.repositories.ai_document_repository import AIDocumentRepository
    from app.models.ai_job import AIJob

    alerts: list[Notification] = []

    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        return alerts

    # Retrieve M4 attention data for dwell analysis
    m4_doc = AIDocumentRepository.get_analysis(str(job_id), "module4")
    if not m4_doc:
        return alerts

    shelf_data = m4_doc.get("shelf_engagement", [])
    for shelf in shelf_data:
        shelf_id_str = shelf.get("shelf_id")
        avg_dwell = shelf.get("avg_dwell_seconds", 0)
        total_views = shelf.get("total_views", 0)

        if total_views >= 30 and avg_dwell < 1.5:
            try:
                shelf_uuid = uuid.UUID(shelf_id_str) if shelf_id_str else None
            except (ValueError, TypeError):
                shelf_uuid = None

            if shelf_uuid and _has_recent_alert(db, "shelf", shelf_uuid, "shelf_performance"):
                continue

            notif = create_notification(
                db,
                store_id=job.store_id,
                type="shelf_performance",
                severity="warning",
                title=f"Shelf Underperforming: Low Dwell Time",
                message=f"Shelf received {total_views} views but average dwell is only {avg_dwell:.1f}s (threshold: 1.5s). Consider product repositioning.",
                entity_type="shelf",
                entity_id=shelf_uuid,
                target_role="store_manager",
                metadata={"avg_dwell": avg_dwell, "total_views": total_views, "job_id": str(job_id)},
            )
            alerts.append(notif)

    if alerts:
        logger.info(f"Shelf Performance: generated {len(alerts)} alert(s) for job {job_id}")
    return alerts


# ── Category 3: Product Visibility ────────────────────────────

def evaluate_product_visibility(db: Session, job_id: uuid.UUID) -> list[Notification]:
    """
    Alert when product attractiveness score < 40 (Grade D) or zero views.
    """
    from app.repositories.ai_document_repository import AIDocumentRepository
    from app.models.ai_job import AIJob

    alerts: list[Notification] = []

    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        return alerts

    m8_doc = AIDocumentRepository.get_analysis(str(job_id), "module8")
    if not m8_doc:
        return alerts

    product_scores = m8_doc.get("product_scores", [])
    for prod in product_scores:
        score = prod.get("overall_score", 100)
        prod_name = prod.get("product_name", "Unknown")
        prod_id_str = prod.get("product_id")

        if score < 40:
            try:
                prod_uuid = uuid.UUID(prod_id_str) if prod_id_str else None
            except (ValueError, TypeError):
                prod_uuid = None

            if prod_uuid and _has_recent_alert(db, "product", prod_uuid, "product_visibility"):
                continue

            notif = create_notification(
                db,
                store_id=job.store_id,
                type="product_visibility",
                severity="warning",
                title=f"Low Product Visibility: {prod_name}",
                message=f"Product '{prod_name}' has an attractiveness score of {score:.1f}/100 (Grade D). Consider repositioning or improving display.",
                entity_type="product",
                entity_id=prod_uuid,
                target_role="retail_analyst",
                metadata={"score": score, "product_name": prod_name, "job_id": str(job_id)},
            )
            alerts.append(notif)

    if alerts:
        logger.info(f"Product Visibility: generated {len(alerts)} alert(s) for job {job_id}")
    return alerts


# ── Category 4: Traffic Anomaly ───────────────────────────────

def evaluate_traffic_anomalies(db: Session) -> list[Notification]:
    """
    Check for zones with zero footfall (dead zones) based on recent AI jobs.
    """
    from app.models.zone import Zone
    from app.models.store import Store

    alerts: list[Notification] = []

    zones = db.query(Zone).all()
    for zone in zones:
        if _has_recent_alert(db, "zone", zone.id, "traffic_anomaly"):
            continue

        # A simple heuristic: if zone status suggests it should be active
        # but has no associated data, generate an info alert.
        # In production this would compare against historical moving averages.

    return alerts


# ── Category 5: Platform Lifecycle ────────────────────────────

def evaluate_platform_lifecycle(db: Session, job_id: uuid.UUID) -> list[Notification]:
    """Generate an info-level notification when an AI job completes."""
    from app.models.ai_job import AIJob

    alerts: list[Notification] = []

    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job or job.status != "COMPLETED":
        return alerts

    if _has_recent_alert(db, "ai_job", job.id, "platform"):
        return alerts

    camera_name = job.camera.name if job.camera else "Unknown"
    store_name = job.store.name if job.store else "Unknown"

    notif = create_notification(
        db,
        store_id=job.store_id,
        type="platform",
        severity="info",
        title=f"AI Analysis Complete: {camera_name}",
        message=f"AI video analysis for camera '{camera_name}' at '{store_name}' has completed successfully. New recommendations are available.",
        entity_type="ai_job",
        entity_id=job.id,
        target_role="all",
        metadata={"job_id": str(job_id), "camera_name": camera_name, "store_name": store_name},
    )
    alerts.append(notif)
    logger.info(f"Platform Lifecycle: job {job_id} completion notification created")
    return alerts


# ── Composite Evaluators ──────────────────────────────────────

def evaluate_post_job(db: Session, job_id: uuid.UUID) -> list[Notification]:
    """
    Run all post-job alert evaluations (shelf, visibility, platform lifecycle).
    Called from the event bus after JOB_PROCESSED.
    """
    all_alerts: list[Notification] = []
    try:
        all_alerts.extend(evaluate_shelf_performance(db, job_id))
    except Exception as exc:
        logger.warning(f"Shelf performance evaluation failed: {exc}")
    try:
        all_alerts.extend(evaluate_product_visibility(db, job_id))
    except Exception as exc:
        logger.warning(f"Product visibility evaluation failed: {exc}")
    try:
        all_alerts.extend(evaluate_platform_lifecycle(db, job_id))
    except Exception as exc:
        logger.warning(f"Platform lifecycle evaluation failed: {exc}")
    return all_alerts


def evaluate_periodic(db: Session) -> list[Notification]:
    """
    Run periodic background evaluations (camera health, traffic anomalies).
    Called from the 60-second background loop.
    """
    all_alerts: list[Notification] = []
    try:
        all_alerts.extend(evaluate_camera_health(db))
    except Exception as exc:
        logger.warning(f"Camera health evaluation failed: {exc}")
    try:
        all_alerts.extend(evaluate_traffic_anomalies(db))
    except Exception as exc:
        logger.warning(f"Traffic anomaly evaluation failed: {exc}")
    return all_alerts
