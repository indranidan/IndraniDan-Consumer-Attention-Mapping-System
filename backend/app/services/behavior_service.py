"""
Module 6 Service
================
Business logic for Module 6 Consumer Behavior Intelligence Analysis:
- Ingests Module 3/4/5 data without reprocessing videos.
- Idempotent analysis execution with deterministic configuration hashing.
- Protects against duplicate concurrent analysis execution via per-job thread locking.
- Persists behavior analysis to MongoDB with disk fallback.
- Serves segmentation, journeys, transitions, funnel, and friction points.
"""

import hashlib
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional
import uuid
from datetime import datetime, timezone

import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi import HTTPException, status
from app.models.ai_job import AIJob
from app.models.camera import Camera
from app.models.store import Store
from ai.behavior_analysis.engine import Module6BehaviorEngine
from app.repositories.ai_document_repository import AIDocumentRepository
from app.services import attention_service as module4_service
from app.services import interaction_service as module5_service

logger = logging.getLogger("module6_service")

# ── Per-Job Concurrency Locks (Thread-safe) ────────────────────────────
_m6_locks: Dict[str, threading.Lock] = {}
_m6_global_lock = threading.Lock()



def _get_m6_job_lock(job_id: uuid.UUID) -> threading.Lock:
    """Retrieve or create a thread-safe mutex for the specific AI job."""
    key = str(job_id)
    with _m6_global_lock:
        if key not in _m6_locks:
            _m6_locks[key] = threading.Lock()
        return _m6_locks[key]


def _get_project_root() -> Path:
    """Determine the project root directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir.parent


def compute_m6_config_hash(
    job_id: uuid.UUID,
    store_id: uuid.UUID,
    camera_id: uuid.UUID,
    m4_analysis_timestamp: Optional[str] = None,
    m5_analysis_timestamp: Optional[str] = None,
    job_completed_at: Optional[datetime] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash of all configuration and upstream inputs
    that govern Module 6 behavior analysis.
    """
    hasher = hashlib.sha256()

    hasher.update(str(job_id).encode("utf-8"))
    hasher.update(str(store_id).encode("utf-8"))
    hasher.update(str(camera_id).encode("utf-8"))

    if m4_analysis_timestamp:
        hasher.update(str(m4_analysis_timestamp).encode("utf-8"))
    if m5_analysis_timestamp:
        hasher.update(str(m5_analysis_timestamp).encode("utf-8"))
    if job_completed_at:
        hasher.update(job_completed_at.isoformat().encode("utf-8"))

    return hasher.hexdigest()


def run_module6_analysis(
    job_id: uuid.UUID,
    db: Session,
    force_recompute: bool = False,
) -> Dict[str, Any]:
    """
    Run the complete Module 6 behavior analysis for a completed AI job.
    Uses cached analysis if inputs and configuration have not changed.
    """
    lock = _get_m6_job_lock(job_id)
    with lock:
        # 1. Fetch AI Job and dependencies
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AI Job {job_id} not found."
            )
        job_status = (job.status or "").upper()
        if job_status not in ["COMPLETED", "FAILED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"AI Job {job_id} must be completed to run behavior analysis (current status: {job.status})."
            )

        camera = db.query(Camera).filter(Camera.id == job.camera_id).first()
        store_id = camera.store_id if camera else (job.store_id or uuid.UUID(int=0))

        # 2. Fetch upstream analysis data (M4, M5) to get their update timestamps
        m4_data = AIDocumentRepository.get_module4_analysis_sync(str(job_id))
        m5_data = AIDocumentRepository.get_module5_analysis_sync(str(job_id))

        m4_timestamp = m4_data.get("updated_at") if isinstance(m4_data, dict) else None
        m5_timestamp = m5_data.get("updated_at") if isinstance(m5_data, dict) else None

        # 3. Compute Config Hash
        current_hash = compute_m6_config_hash(
            job_id=job.id,
            store_id=store_id,
            camera_id=job.camera_id,
            m4_analysis_timestamp=m4_timestamp,
            m5_analysis_timestamp=m5_timestamp,
            job_completed_at=job.completed_at,
        )

        # 4. Check for cached analysis
        if not force_recompute:
            cached = AIDocumentRepository.get_module6_analysis_sync(str(job_id))
            if cached and cached.get("summary"):
                cached_hash = cached.get("config_hash")
                if cached_hash is None or cached_hash == current_hash:
                    logger.info(f"Module 6 analysis for job {job_id} is up to date (cache hit).")
                    return cached

        # 5. Fetch M3 Data (Movement reports & sessions)
        project_root = _get_project_root()
        output_dir = None
        if job.output_path:
            op = Path(job.output_path)
            output_dir = op if op.is_absolute() else (project_root / op)
        if not output_dir or not output_dir.exists():
            output_dir = project_root / "outputs" / "ai_jobs" / str(job_id)

        # Build M3 data dict from disk / MongoDB
        import json
        m3_data = {"sessions": [], "shoppers": []}

        for session_cand in [
            output_dir / "phase3" / "reports" / "sessions.json",
            output_dir / "phase2" / "reports" / "sessions.json",
            output_dir / "reports" / "sessions.json",
        ]:
            if session_cand.exists():
                try:
                    with open(session_cand, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        m3_data["sessions"] = data.get("sessions", data if isinstance(data, list) else [])
                        if m3_data["sessions"]:
                            break
                except Exception as e:
                    logger.warning(f"Failed to read {session_cand}: {e}")

        for path_cand in [
            output_dir / "phase3" / "reports" / "paths.json",
            output_dir / "phase2" / "reports" / "tracks.json",
            output_dir / "phase2" / "reports" / "movement_report.json",
            output_dir / "phase2" / "reports" / "tracking_report.json",
        ]:
            if path_cand.exists():
                try:
                    with open(path_cand, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            if "paths" in data and isinstance(data["paths"], dict):
                                m3_data["paths"] = data["paths"]
                                m3_data["shoppers"] = [
                                    {"tracking_id": int(k) if str(k).isdigit() else k, "path": v}
                                    for k, v in data["paths"].items()
                                ]
                            elif "shoppers" in data and isinstance(data["shoppers"], list):
                                m3_data["shoppers"] = data["shoppers"]
                            elif "tracks" in data and isinstance(data["tracks"], list):
                                m3_data["shoppers"] = data["tracks"]
                        elif isinstance(data, list):
                            m3_data["shoppers"] = data
                        if m3_data["shoppers"] or m3_data.get("paths"):
                            break
                except Exception as e:
                    logger.warning(f"Failed to read {path_cand}: {e}")

        # Construct M4 and M5 input formats
        m4_events_tuple = AIDocumentRepository.get_attention_events_sync(str(job_id))
        m4_events = m4_events_tuple[0] if m4_events_tuple else []
        if not m4_events:
            for m4_cand in [
                output_dir / "phase5" / "reports" / "attention_events.json",
                output_dir / "module4" / "module4_attention_report.json",
            ]:
                if m4_cand.exists():
                    try:
                        with open(m4_cand, "r", encoding="utf-8") as f:
                            m4_json = json.load(f)
                            m4_events = m4_json.get("events", m4_json.get("attention_events", []))
                            if m4_events:
                                break
                    except Exception:
                        pass
        m4_input = {"attention_events": m4_events}

        m5_events_tuple = AIDocumentRepository.get_interaction_events_sync(str(job_id))
        m5_events = m5_events_tuple[0] if m5_events_tuple else []
        if not m5_events:
            m5_cand = output_dir / "module5" / "module5_interaction_report.json"
            if m5_cand.exists():
                try:
                    with open(m5_cand, "r", encoding="utf-8") as f:
                        m5_json = json.load(f)
                        m5_events = m5_json.get("events", m5_json.get("interactions", []))
                except Exception:
                    pass
        m5_input = {"events": m5_events}


        # 6. Execute Module 6 Engine
        logger.info(f"Executing Module 6 Behavior Analysis for job {job_id}...")
        engine = Module6BehaviorEngine()
        
        try:
            analysis_result = engine.analyze(
                m3_data=m3_data,
                m4_data=m4_input,
                m5_data=m5_input,
                store_id=str(store_id),
                camera_id=str(job.camera_id),
                job_id=str(job_id),
            )
            
            # Attach metadata
            analysis_result["config_hash"] = current_hash
            analysis_result["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # 7. Persist to MongoDB
            AIDocumentRepository.save_module6_analysis_sync(job_id, analysis_result)
            logger.info(f"Module 6 analysis completed and persisted for job {job_id}.")
            
            return analysis_result
            
        except Exception as exc:
            logger.error(f"Module 6 analysis failed for job {job_id}: {exc}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Module 6 behavior analysis failed: {str(exc)}"
            )


def get_module6_analysis(
    job_id: uuid.UUID,
    db: Session,
) -> Optional[Dict[str, Any]]:
    """Retrieve existing Module 6 analysis without recomputing."""
    return AIDocumentRepository.get_module6_analysis_sync(str(job_id))


def get_or_run_module6_analysis(
    job_id: uuid.UUID,
    db: Session,
    force_recompute: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve existing Module 6 behavior analysis or run it on-demand for completed jobs.
    Matches the get_or_run_module4_analysis and get_or_run_module5_analysis lifecycle pattern.
    """
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI job with id '{job_id}' not found.",
        )

    if job.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job is not completed yet (status: {job.status}).",
        )

    # 1. Fast-path check: Return cached analysis if present and not force_recompute
    if not force_recompute:
        cached = AIDocumentRepository.get_module6_analysis_sync(str(job_id))
        if cached and cached.get("summary"):
            return cached

    # 2. Compute on-demand under per-job lock
    return run_module6_analysis(job_id=job_id, db=db, force_recompute=force_recompute)

