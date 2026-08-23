"""
Module 4 Service
==================
Business logic for Module 4 Attention Engine:
- Ingests completed Module 3 jobs without re-running YOLO or ByteTrack.
- Implements idempotent analysis execution with deterministic configuration hashing.
- Protects against duplicate concurrent analysis execution via per-job thread locking.
- Persists aggregate analysis and event records to MongoDB with disk fallback.
- Serves shelf engagement, product attention, events, reports, and heatmaps.
"""

import hashlib
import json
import logging
from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Tuple
import uuid
from datetime import datetime, timezone

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

# pyrefly: ignore [missing-import]
from app.models.ai_job import AIJob
# pyrefly: ignore [missing-import]
from app.models.camera import Camera
# pyrefly: ignore [missing-import]
from app.models.product import Product
# pyrefly: ignore [missing-import]
from app.models.shelf import Shelf
from app.models.store import Store
from app.modules.attention.engine import Module4AttentionEngine
from app.modules.attention.report_generator import Module4ReportGenerator
from app.repositories.ai_document_repository import AIDocumentRepository
from app.schemas.attention import (
    AttentionEventItem,
    Module4AnalysisResponse,
    Module4HeatmapResponse,
    Module4QualityMetrics,
    Module4ReportResponse,
    Module4SummarySchema,
    ProductMetricItem,
    ShelfMetricItem,
)

logger = logging.getLogger("module4_service")

# ── Per-Job Concurrency Locks ──────────────────────────────────────────
_m4_locks: Dict[str, threading.Lock] = {}
_m4_global_lock = threading.Lock()


def _get_m4_job_lock(job_id: uuid.UUID) -> threading.Lock:
    """Retrieve or create a thread-safe mutex for the specific AI job."""
    key = str(job_id)
    with _m4_global_lock:
        if key not in _m4_locks:
            _m4_locks[key] = threading.Lock()
        return _m4_locks[key]


def _get_project_root() -> Path:
    """Determine the project root directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir.parent


def compute_m4_config_hash(
    job_id: uuid.UUID,
    store_id: uuid.UUID,
    camera_id: uuid.UUID,
    db_shelves: List[Shelf],
    regions_file_path: Optional[Path] = None,
    job_completed_at: Optional[datetime] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash of all configuration and upstream inputs
    that govern Module 4 Attention Engine analysis.
    """
    hasher = hashlib.sha256()

    hasher.update(str(job_id).encode("utf-8"))
    hasher.update(str(store_id).encode("utf-8"))
    hasher.update(str(camera_id).encode("utf-8"))

    shelves_repr = sorted(
        [
            f"{s.id}:{s.shelf_code}:{s.name}:{s.zone_id}:{getattr(s, 'bounding_polygon', '')}"
            for s in db_shelves
        ]
    )
    hasher.update(";".join(shelves_repr).encode("utf-8"))

    if regions_file_path and regions_file_path.exists():
        try:
            with open(regions_file_path, "rb") as f:
                hasher.update(f.read())
        except Exception:
            pass

    return hasher.hexdigest()


def _check_module3_outputs_exist(output_dir: Path) -> bool:
    """Verify that all required upstream Module 3 artifacts are available."""
    phase4_dwell = output_dir / "phase4" / "reports" / "zone_dwell_summary.json"
    phase5_attn = output_dir / "phase5" / "reports" / "target_attention_summary.json"
    phase3_tracks = output_dir / "phase3" / "reports" / "sessions.json"

    return phase4_dwell.exists() or phase5_attn.exists() or phase3_tracks.exists()


def _build_analysis_response_from_dict(
    job: AIJob,
    analysis_dict: Dict[str, Any],
    output_dir: Optional[Path] = None,
) -> Module4AnalysisResponse:
    """Construct Module4AnalysisResponse schema from MongoDB analysis dict."""
    summary_raw = analysis_dict.get("summary", {})
    shelves_raw = analysis_dict.get("shelves", [])
    products_raw = analysis_dict.get("products", [])
    quality_raw = analysis_dict.get("quality_metrics", {})
    heatmap_raw = analysis_dict.get("heatmap", {})

    summary_schema = Module4SummarySchema(
        total_attention_events=summary_raw.get("total_attention_events", 0),
        total_attention_duration_sec=summary_raw.get("total_attention_duration_sec", 0.0),
        average_attention_duration_sec=summary_raw.get("average_attention_duration_sec", 0.0),
        shelf_engagement_score_avg=summary_raw.get("shelf_engagement_score_avg", 0.0),
        total_shelves_monitored=summary_raw.get("total_shelves_monitored", len(shelves_raw)),
        active_shelves=summary_raw.get("active_shelves", len(shelves_raw)),
        total_products_tracked=summary_raw.get("total_products_tracked", len(products_raw)),
        most_viewed_shelf_id=summary_raw.get("most_viewed_shelf_id"),
        most_viewed_shelf_name=summary_raw.get("most_viewed_shelf_name"),
        most_viewed_product_id=summary_raw.get("most_viewed_product_id"),
        most_viewed_product_name=summary_raw.get("most_viewed_product_name"),
        config_hash=summary_raw.get("config_hash"),
        analyzed_at=summary_raw.get("analyzed_at"),
        version=summary_raw.get("version", "1.1"),
    )

    shelves_schema = [ShelfMetricItem(**s) for s in shelves_raw]
    products_schema = [ProductMetricItem(**p) for p in products_raw]
    quality_schema = Module4QualityMetrics(**quality_raw) if quality_raw else None

    return Module4AnalysisResponse(
        job_id=job.id,
        camera_id=job.camera_id,
        store_id=job.store_id,
        status="COMPLETED",
        summary=summary_schema,
        shelves=shelves_schema,
        products=products_schema,
        quality_metrics=quality_schema,
        heatmap=heatmap_raw,
    )


def get_module4_analysis(db: Session, job_id: uuid.UUID) -> Module4AnalysisResponse:
    """
    Retrieve existing Module 4 analysis results for a job.
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

    existing_analysis = AIDocumentRepository.get_module4_analysis_sync(str(job_id))
    project_root = _get_project_root()
    output_dir = None
    if job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    if not existing_analysis and output_dir:
        disk_file = output_dir / "module4" / "module4_attention_report.json"
        if disk_file.exists():
            try:
                with open(disk_file, "r", encoding="utf-8") as f:
                    existing_analysis = json.load(f)
            except Exception:
                pass

    if not existing_analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module 4 analysis has not been generated for this job yet.",
        )

    return _build_analysis_response_from_dict(job, existing_analysis, output_dir)


def run_module4_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = True,
) -> Module4AnalysisResponse:
    """
    Explicitly execute Module 4 Attention Engine on completed Module 3 outputs.
    """
    return get_or_run_module4_analysis(db, job_id, force_rerun=force_rerun)


def get_or_run_module4_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = False,
) -> Module4AnalysisResponse:
    """
    Retrieve existing Module 4 analysis for a job, or run it on completed Module 3 outputs.
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

    # 1. Fetch shelves and compute input config hash
    db_shelves = db.query(Shelf).filter(Shelf.store_id == job.store_id).all()
    regions_file = project_root / "ai" / "configs" / "attention_regions.json"
    current_config_hash = compute_m4_config_hash(
        job_id=job.id,
        store_id=job.store_id,
        camera_id=job.camera_id,
        db_shelves=db_shelves,
        regions_file_path=regions_file if regions_file.exists() else None,
        job_completed_at=job.completed_at,
    )

    # 2. Fast-path check: Return persisted result from MongoDB if valid and not force_rerun
    if not force_rerun:
        existing_analysis = AIDocumentRepository.get_module4_analysis_sync(str(job_id))
        if existing_analysis and existing_analysis.get("summary"):
            stored_hash = existing_analysis.get("summary", {}).get("config_hash")
            if stored_hash is None or stored_hash == current_config_hash:
                return _build_analysis_response_from_dict(job, existing_analysis, output_dir)

    # 3. Synchronized Execution under per-job lock
    if not output_dir or not output_dir.exists() or not _check_module3_outputs_exist(output_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Module 3 analysis data available for this job.",
        )

    job_lock = _get_m4_job_lock(job_id)
    with job_lock:
        if not force_rerun:
            existing_analysis = AIDocumentRepository.get_module4_analysis_sync(str(job_id))
            if existing_analysis and existing_analysis.get("summary"):
                stored_hash = existing_analysis.get("summary", {}).get("config_hash")
                if stored_hash is None or stored_hash == current_config_hash:
                    return _build_analysis_response_from_dict(job, existing_analysis, output_dir)

        shelf_regions = []
        if regions_file.exists():
            try:
                with open(regions_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    shelf_regions.extend(cfg.get("regions", []))
            except Exception:
                pass

        for s in db_shelves:
            for r in shelf_regions:
                if (s.shelf_code and s.shelf_code == r.get("id")) or (
                    s.name and s.name.lower() == r.get("name", "").lower()
                ):
                    r["shelf_code"] = s.shelf_code
                    r["db_id"] = str(s.id)
                    if s.zone:
                        r["zone_id"] = s.zone.zone_code or str(s.zone.id)

        db_products = db.query(Product).filter(Product.store_id == job.store_id).all()
        product_list = [
            {
                "id": str(p.id),
                "name": p.name,
                "sku": p.sku,
                "shelf_id": str(p.shelf_id),
                "shelf_name": p.shelf.name if p.shelf else "Unknown",
            }
            for p in db_products
        ]

        try:
            engine = Module4AttentionEngine()
            report_dict = engine.process_completed_module3_job(
                job_output_dir=output_dir,
                shelf_regions=shelf_regions,
                product_mappings=product_list,
                store_id=str(job.store_id),
                camera_id=str(job.camera_id),
            )
        except Exception as exc:
            logger.error(f"Module 4 Attention Engine failed for job {job_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Module 4 analysis failed: {str(exc)}. Retry available.",
            )

        summary_raw = report_dict.get("summary", {})
        shelves_raw = report_dict.get("shelves", [])
        products_raw = (
            report_dict.get("products", [])
            or engine.product_detector.get_unconfigured_placeholder(product_list)
        )
        quality_raw = report_dict.get("quality_metrics", {})
        heatmap_raw = report_dict.get("heatmap", {})
        events_sample = report_dict.get("events_sample", [])

        if not products_raw and product_list:
            products_raw = [
                p.to_dict()
                for p in engine.product_detector.get_unconfigured_placeholder(product_list)
            ]

        summary_raw["config_hash"] = current_config_hash
        summary_raw["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        summary_raw["version"] = "1.1"

        analysis_dict = {
            "summary": summary_raw,
            "shelves": shelves_raw,
            "products": [p if isinstance(p, dict) else p.to_dict() for p in products_raw],
            "quality_metrics": quality_raw,
            "heatmap": heatmap_raw,
        }

        # Persist into MongoDB
        AIDocumentRepository.save_module4_analysis_sync(job.id, analysis_dict, events=events_sample)

        # Write reports to disk cache
        try:
            m4_dir = output_dir / "module4"
            m4_dir.mkdir(parents=True, exist_ok=True)
            with open(m4_dir / "module4_attention_report.json", "w", encoding="utf-8") as f:
                json.dump(report_dict, f, indent=2, default=str)

            report_gen = Module4ReportGenerator()
            md_content = report_gen.generate_markdown_report(report_dict)
            with open(m4_dir / "module4_attention_report.md", "w", encoding="utf-8") as f:
                f.write(md_content)
        except Exception as file_exc:
            logger.warning(f"Failed to write Module 4 disk artifacts: {file_exc}")

        return _build_analysis_response_from_dict(job, analysis_dict, output_dir)


def get_shelf_metrics(db: Session, job_id: uuid.UUID) -> List[ShelfMetricItem]:
    """Retrieve shelf metrics for a completed job (read-only)."""
    analysis = get_module4_analysis(db, job_id)
    return analysis.shelves


def get_product_metrics(db: Session, job_id: uuid.UUID) -> List[ProductMetricItem]:
    """Retrieve product metrics for a completed job (read-only)."""
    analysis = get_module4_analysis(db, job_id)
    return analysis.products


def get_attention_events(
    db: Session,
    job_id: uuid.UUID,
    track_id: Optional[int] = None,
    target_id: Optional[str] = None,
    target_type: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Tuple[List[AttentionEventItem], int]:
    """
    Retrieve granular attention events with optional filters from MongoDB (with disk fallback).
    """
    records, total = AIDocumentRepository.get_attention_events_sync(
        str(job_id),
        track_id=track_id,
        target_id=target_id,
        target_type=target_type,
        page=page,
        page_size=page_size,
    )

    if not records:
        # Fallback to loading sample from disk if MongoDB has no records
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        if job and job.output_path:
            project_root = _get_project_root()
            op = Path(job.output_path)
            output_dir = op if op.is_absolute() else (project_root / op)
            json_file = output_dir / "module4" / "module4_attention_report.json"
            if json_file.exists():
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    records = data.get("events_sample", [])
                    total = len(records)
                except Exception:
                    pass

    items = [
        AttentionEventItem(
            event_id=str(r.get("_id") or r.get("event_id") or uuid.uuid4()),
            track_id=int(r.get("track_id") or r.get("tracking_id") or 0),
            session_id=r.get("session_id"),
            camera_id=None,
            store_id=None,
            timestamp=float(r.get("start_time") or r.get("timestamp") or 0.0),
            start_time=float(r.get("start_time") or 0.0),
            end_time=float(r.get("end_time")) if r.get("end_time") is not None else None,
            duration_seconds=float(r.get("duration_seconds") or 0.0),
            attention_type="SHELF_ATTENTION" if r.get("target_type") == "shelf" else "HEAD_POSE_ATTENTION",
            target_type=r.get("target_type", "shelf"),
            target_id=str(r.get("target_id", "unknown")),
            target_name=str(r.get("target_name", "Unknown")),
            zone_id=str(r.get("zone_id", "unknown")),
            attention_direction=str(r.get("attention_direction", "UNKNOWN")),
            confidence=float(r.get("confidence") or 0.8),
            status="completed",
            visit_number=int(r.get("visit_number") or 1),
        )
        for r in records
    ]
    return items, total


def get_module4_report(db: Session, job_id: uuid.UUID) -> Module4ReportResponse:
    """Retrieve full JSON and Markdown report for Module 4 (read-only)."""
    analysis = get_module4_analysis(db, job_id)
    job = db.query(AIJob).filter(AIJob.id == job_id).first()

    project_root = _get_project_root()
    output_dir = None
    if job and job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    md_file = output_dir / "module4" / "module4_attention_report.md" if output_dir else None
    json_file = output_dir / "module4" / "module4_attention_report.json" if output_dir else None

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
        report_gen = Module4ReportGenerator()
        md_content = report_gen.generate_markdown_report(json_content)

    return Module4ReportResponse(
        job_id=job_id,
        camera_id=job.camera_id if job else None,
        store_id=job.store_id if job else None,
        json_report=json_content,
        markdown_report=md_content,
    )


def get_attention_heatmaps(db: Session, job_id: uuid.UUID) -> Module4HeatmapResponse:
    """Retrieve attention heatmap matrix data."""
    analysis = get_or_run_module4_analysis(db, job_id, force_rerun=False)
    raw_heatmap = analysis.heatmap or {}
    points = raw_heatmap.get("points", [])

    image_url = raw_heatmap.get("image_url") or f"/api/ai/results/{job_id}/files/module4/attention_heatmap.png"

    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    project_root = _get_project_root()
    if job and job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)
        heatmap_path = output_dir / "module4" / "attention_heatmap.png"
        if not heatmap_path.exists():
            try:
                events_items, _ = get_attention_events(db, job_id=job_id)
                if events_items:
                    from app.modules.attention.heatmap_generator import Module4HeatmapGenerator
                    from app.modules.attention.models import AttentionEventRecord
                    records = [
                        AttentionEventRecord(
                            event_id=e.event_id,
                            track_id=e.track_id,
                            timestamp=e.timestamp,
                            start_time=e.start_time,
                            end_time=e.end_time,
                            duration_seconds=e.duration_seconds,
                            target_id=e.target_id,
                            target_name=e.target_name,
                            attention_direction=e.attention_direction,
                            confidence=e.confidence,
                        )
                        for e in events_items
                    ]
                    gen = Module4HeatmapGenerator()
                    gen.render_heatmap_image(records, heatmap_path)
            except Exception as exc:
                logger.warning(f"Could not render missing heatmap image: {exc}")

    return Module4HeatmapResponse(
        job_id=job_id,
        camera_width=raw_heatmap.get("camera_width", raw_heatmap.get("grid_width", 1920)),
        camera_height=raw_heatmap.get("camera_height", raw_heatmap.get("grid_height", 1080)),
        total_points=raw_heatmap.get("total_points", len(points)),
        points=points,
        image_url=image_url,
    )


# Backward-compatible aliases
get_module4_heatmap = get_attention_heatmaps
get_attention_heatmap = get_attention_heatmaps
get_attention_report = get_module4_report
get_attention_analysis = get_or_run_module4_analysis

