"""
Module 5 Service
==================
Business logic for Module 5 Product Interaction Analysis Module:
- Ingests Module 3 tracking/dwell and Module 4 attention data without reprocessing videos.
- Idempotent analysis execution with deterministic configuration hashing.
- Protects against duplicate concurrent analysis execution via per-job thread locking.
- Persists aggregate analysis and event records to MongoDB with disk fallback.
- Serves product engagement, shelf interactions, events, comparisons, and reports.
"""

import hashlib
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.camera import Camera
from app.models.product import Product
from app.models.shelf import Shelf
from app.models.store import Store
from app.modules.interaction.engine import Module5InteractionEngine
from app.modules.interaction.report_generator import Module5ReportGenerator
from app.repositories.ai_document_repository import AIDocumentRepository
from app.schemas.interaction import (
    InteractionEventItem,
    Module5AnalysisResponse,
    Module5ReportResponse,
    Module5SummarySchema,
    ProductComparisonItem,
    ProductEngagementItem,
    ShelfInteractionItem,
)
from app.services import attention_service as module4_service

logger = logging.getLogger("module5_service")

# ── Per-Job Concurrency Locks ──────────────────────────────────────────
_m5_locks: Dict[str, threading.Lock] = {}
_m5_global_lock = threading.Lock()


def _get_m5_job_lock(job_id: uuid.UUID) -> threading.Lock:
    """Retrieve or create a thread-safe mutex for the specific AI job."""
    key = str(job_id)
    with _m5_global_lock:
        if key not in _m5_locks:
            _m5_locks[key] = threading.Lock()
        return _m5_locks[key]


def _get_project_root() -> Path:
    """Determine the project root directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir.parent


def compute_m5_config_hash(
    job_id: uuid.UUID,
    store_id: uuid.UUID,
    camera_id: uuid.UUID,
    db_products: List[Product],
    db_shelves: List[Shelf],
    m4_analysis_timestamp: Optional[str] = None,
    job_completed_at: Optional[datetime] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash of all configuration and upstream inputs
    that govern Module 5 Product Interaction analysis.
    """
    hasher = hashlib.sha256()

    hasher.update(str(job_id).encode("utf-8"))
    hasher.update(str(store_id).encode("utf-8"))
    hasher.update(str(camera_id).encode("utf-8"))

    products_repr = sorted(
        [
            f"{p.id}:{p.name}:{p.sku}:{p.shelf_id}:{getattr(p, 'price', 0.0)}"
            for p in db_products
        ]
    )
    hasher.update(";".join(products_repr).encode("utf-8"))

    shelves_repr = sorted(
        [
            f"{s.id}:{s.shelf_code}:{s.name}:{s.zone_id}"
            for s in db_shelves
        ]
    )
    hasher.update(";".join(shelves_repr).encode("utf-8"))

    return hasher.hexdigest()


def _check_upstream_outputs_exist(output_dir: Path) -> bool:
    """Verify that required Module 3 tracking/dwell artifacts exist."""
    phase4_dwell = output_dir / "phase4" / "reports" / "zone_dwell_summary.json"
    phase5_attn = output_dir / "phase5" / "reports" / "target_attention_summary.json"
    phase3_tracks = output_dir / "phase3" / "reports" / "sessions.json"

    return phase4_dwell.exists() or phase5_attn.exists() or phase3_tracks.exists()


def _build_analysis_response_from_dict(
    job: AIJob,
    analysis_dict: Dict[str, Any],
    event_count: int = 0,
) -> Module5AnalysisResponse:
    """Construct Module5AnalysisResponse schema from MongoDB analysis dict."""
    summary_raw = analysis_dict.get("summary", {})
    products_raw = analysis_dict.get("products", [])
    shelves_raw = analysis_dict.get("shelves", [])
    comparisons_raw = analysis_dict.get("comparisons", [])

    summary_schema = Module5SummarySchema(
        total_views=summary_raw.get("total_views", 0),
        total_pickups=summary_raw.get("total_pickups", 0),
        total_returns=summary_raw.get("total_returns", 0),
        total_comparisons=summary_raw.get("total_comparisons", 0),
        total_purchases=summary_raw.get("total_purchases", 0),
        total_unique_viewers=summary_raw.get("total_unique_viewers", 0),
        total_engagement_duration_sec=summary_raw.get("total_engagement_duration_sec", 0.0),
        avg_pickup_to_return_seconds=summary_raw.get("avg_pickup_to_return_seconds", 0.0),
        pickup_rate_percentage=summary_raw.get("pickup_rate_percentage", 0.0),
        return_rate_percentage=summary_raw.get("return_rate_percentage", 0.0),
        conversion_rate_percentage=summary_raw.get("conversion_rate_percentage", 0.0),
        pickup_detection_status=summary_raw.get("pickup_detection_status", "INSUFFICIENT_VISUAL_EVIDENCE"),
        purchase_data_status=summary_raw.get("purchase_data_status", "UNAVAILABLE / NOT CONFIGURED (No POS Data)"),
        most_engaged_product_id=summary_raw.get("most_engaged_product_id"),
        most_engaged_product_name=summary_raw.get("most_engaged_product_name"),
        most_compared_product_id=summary_raw.get("most_compared_product_id"),
        most_compared_product_name=summary_raw.get("most_compared_product_name"),
        config_hash=summary_raw.get("config_hash"),
        analyzed_at=summary_raw.get("analyzed_at"),
        version=summary_raw.get("version", "1.0"),
    )

    products_schema = [ProductEngagementItem(**p) for p in products_raw]
    shelves_schema = [ShelfInteractionItem(**s) for s in shelves_raw]
    comparisons_schema = [ProductComparisonItem(**c) for c in comparisons_raw]

    return Module5AnalysisResponse(
        job_id=job.id,
        camera_id=job.camera_id,
        store_id=job.store_id,
        status="COMPLETED",
        summary=summary_schema,
        products=products_schema,
        shelves=shelves_schema,
        comparisons=comparisons_schema,
        total_event_count=event_count or len(analysis_dict.get("events_sample", [])),
    )


def get_module5_analysis(db: Session, job_id: uuid.UUID) -> Module5AnalysisResponse:
    """
    Retrieve existing Module 5 analysis results for a job.
    If no analysis has been executed yet, runs it on demand.
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

    existing_analysis = AIDocumentRepository.get_module5_analysis_sync(str(job_id))
    project_root = _get_project_root()
    output_dir = None
    if job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    if not existing_analysis and output_dir:
        disk_file = output_dir / "module5" / "module5_interaction_report.json"
        if disk_file.exists():
            try:
                with open(disk_file, "r", encoding="utf-8") as f:
                    existing_analysis = json.load(f)
            except Exception:
                pass

    if not existing_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module 5 analysis has not been generated for this job yet.",
        )

    return _build_analysis_response_from_dict(job, existing_analysis)


def run_module5_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = True,
) -> Module5AnalysisResponse:
    """Explicitly execute Module 5 Product Interaction Engine."""
    return get_or_run_module5_analysis(db, job_id, force_rerun=force_rerun)


def get_or_run_module5_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = False,
) -> Module5AnalysisResponse:
    """
    Retrieve existing Module 5 analysis or run it on completed job data.
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

    project_root = _get_project_root()
    output_dir = None
    if job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    # 1. Fetch metadata and compute config hash
    db_products = db.query(Product).filter(Product.store_id == job.store_id).all()
    db_shelves = db.query(Shelf).filter(Shelf.store_id == job.store_id).all()

    # Get upstream Module 4 analysis
    m4_analysis = module4_service.get_or_run_module4_analysis(db, job_id, force_rerun=False)
    m4_analyzed_at = m4_analysis.summary.analyzed_at if m4_analysis and m4_analysis.summary else None

    current_config_hash = compute_m5_config_hash(
        job_id=job.id,
        store_id=job.store_id,
        camera_id=job.camera_id,
        db_products=db_products,
        db_shelves=db_shelves,
        m4_analysis_timestamp=m4_analyzed_at,
        job_completed_at=job.completed_at,
    )

    # 2. Fast-path check: Return persisted result from MongoDB if valid
    if not force_rerun:
        existing_analysis = AIDocumentRepository.get_module5_analysis_sync(str(job_id))
        if existing_analysis and existing_analysis.get("summary"):
            stored_hash = existing_analysis.get("summary", {}).get("config_hash")
            if stored_hash is None or stored_hash == current_config_hash:
                return _build_analysis_response_from_dict(job, existing_analysis)

    # 3. Synchronized Execution under per-job lock
    if not output_dir or not output_dir.exists() or not _check_upstream_outputs_exist(output_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Module 3 analysis data available for this job.",
        )

    job_lock = _get_m5_job_lock(job_id)
    with job_lock:
        if not force_rerun:
            existing_analysis = AIDocumentRepository.get_module5_analysis_sync(str(job_id))
            if existing_analysis and existing_analysis.get("summary"):
                stored_hash = existing_analysis.get("summary", {}).get("config_hash")
                if stored_hash is None or stored_hash == current_config_hash:
                    return _build_analysis_response_from_dict(job, existing_analysis)

        product_list = [
            {
                "id": str(p.id),
                "name": p.name,
                "sku": p.sku,
                "shelf_id": str(p.shelf_id),
                "shelf_name": p.shelf.name if p.shelf else "Unknown",
                "price": float(p.price) if hasattr(p, "price") and p.price is not None else 0.0,
            }
            for p in db_products
        ]

        shelf_list = [
            {
                "id": str(s.id),
                "name": s.name,
                "shelf_code": s.shelf_code,
                "zone_id": str(s.zone_id) if s.zone_id else None,
            }
            for s in db_shelves
        ]

        try:
            engine = Module5InteractionEngine()
            report_dict = engine.process_completed_job(
                job_output_dir=output_dir,
                configured_products=product_list,
                configured_shelves=shelf_list,
                store_id=str(job.store_id),
                camera_id=str(job.camera_id),
            )
        except Exception as exc:
            logger.error(f"Module 5 Interaction Engine failed for job {job_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Module 5 analysis failed: {str(exc)}. Retry available.",
            )

        summary_raw = report_dict.get("summary", {})
        products_raw = report_dict.get("products", [])
        shelves_raw = report_dict.get("shelves", [])
        comparisons_raw = report_dict.get("comparisons", [])
        events_raw = report_dict.get("events", [])

        summary_raw["config_hash"] = current_config_hash
        summary_raw["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        summary_raw["version"] = "1.0"

        analysis_dict = {
            "summary": summary_raw,
            "products": products_raw,
            "shelves": shelves_raw,
            "comparisons": comparisons_raw,
        }

        # Persist to MongoDB
        AIDocumentRepository.save_module5_analysis_sync(job.id, analysis_dict, events=events_raw)

        # Write reports to disk cache
        try:
            m5_dir = output_dir / "module5"
            m5_dir.mkdir(parents=True, exist_ok=True)
            with open(m5_dir / "module5_interaction_report.json", "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, default=str)

            report_gen = Module5ReportGenerator()
            md_content = report_gen.generate_markdown_report(report_dict)
            with open(m5_dir / "module5_interaction_report.md", "w", encoding="utf-8") as f:
                f.write(md_content)
        except Exception as file_exc:
            logger.warning(f"Failed to write Module 5 disk artifacts: {file_exc}")

        return _build_analysis_response_from_dict(job, analysis_dict, event_count=len(events_raw))


def get_product_engagement(
    db: Session, job_id: uuid.UUID
) -> List[ProductEngagementItem]:
    """Retrieve per-product engagement metrics for a job (read-only)."""
    analysis = get_module5_analysis(db, job_id)
    return analysis.products


def get_shelf_interactions(
    db: Session, job_id: uuid.UUID
) -> List[ShelfInteractionItem]:
    """Retrieve per-shelf interaction metrics for a job (read-only)."""
    analysis = get_module5_analysis(db, job_id)
    return analysis.shelves


def get_interaction_events(
    db: Session,
    job_id: uuid.UUID,
    track_id: Optional[int] = None,
    event_type: Optional[str] = None,
    product_id: Optional[str] = None,
    shelf_id: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Tuple[List[InteractionEventItem], int]:
    """
    Retrieve granular product interaction events with optional filters from MongoDB (with disk fallback).
    """
    records, total = AIDocumentRepository.get_interaction_events_sync(
        str(job_id),
        track_id=track_id,
        event_type=event_type,
        product_id=product_id,
        shelf_id=shelf_id,
        page=page,
        page_size=page_size,
    )

    if not records:
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        if job and job.output_path:
            project_root = _get_project_root()
            op = Path(job.output_path)
            output_dir = op if op.is_absolute() else (project_root / op)
            json_file = output_dir / "module5" / "module5_interaction_report.json"
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    records = data.get("events", [])
                    total = len(records)
                except Exception:
                    pass

    items = [
        InteractionEventItem(
            event_id=str(r.get("event_id") or r.get("_id") or uuid.uuid4()),
            event_type=r.get("event_type", "PRODUCT_VIEWED"),
            track_id=int(r.get("track_id") or r.get("tracking_id") or 0),
            session_id=r.get("session_id"),
            product_id=r.get("product_id"),
            product_name=r.get("product_name"),
            sku=r.get("sku"),
            shelf_id=r.get("shelf_id"),
            shelf_name=r.get("shelf_name"),
            camera_id=None,
            store_id=None,
            timestamp=float(r.get("timestamp") or r.get("start_time") or 0.0),
            start_time=float(r.get("start_time") or 0.0),
            end_time=float(r.get("end_time")) if r.get("end_time") is not None else None,
            duration_seconds=float(r.get("duration_seconds") or 0.0),
            confidence=float(r.get("confidence") or 0.8),
            source=r.get("source", "MODULE_4_ATTENTION"),
            metadata=r.get("metadata") or r.get("metadata_json"),
        )
        for r in records
    ]
    return items, total


def get_product_comparisons(
    db: Session, job_id: uuid.UUID
) -> List[ProductComparisonItem]:
    """Retrieve cross-product comparison sessions for a job (read-only)."""
    analysis = get_module5_analysis(db, job_id)
    return analysis.comparisons


def get_module5_report(
    db: Session, job_id: uuid.UUID
) -> Module5ReportResponse:
    """Retrieve full JSON and Markdown report for Module 5 (read-only)."""
    analysis = get_module5_analysis(db, job_id)
    job = db.query(AIJob).filter(AIJob.id == job_id).first()

    project_root = _get_project_root()
    output_dir = None
    if job and job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    md_file = output_dir / "module5" / "module5_interaction_report.md" if output_dir else None
    json_file = output_dir / "module5" / "module5_interaction_report.json" if output_dir else None

    md_content = ""
    json_content: Dict[str, Any] = {}

    if md_file and md_file.exists():
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                md_content = f.read()
        except Exception:
            pass

    if json_file and json_file.exists():
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                json_content = json.load(f)
        except Exception:
            pass

    if not json_content:
        json_content = analysis.model_dump() if hasattr(analysis, "model_dump") else analysis.dict()

    if not md_content or not md_content.strip():
        report_gen = Module5ReportGenerator()
        md_content = report_gen.generate_markdown_report(json_content)

    return Module5ReportResponse(
        job_id=job_id,
        camera_id=job.camera_id if job else None,
        store_id=job.store_id if job else None,
        json_report=json_content,
        markdown_report=md_content,
    )
