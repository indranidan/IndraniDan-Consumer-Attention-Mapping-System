"""
Module 5 Service
==================
Business logic for Module 5 Product Interaction Analysis Engine:
- Ingests completed Module 3 & Module 4 jobs without re-running YOLO or ByteTrack.
- Implements idempotent analysis execution with deterministic configuration hashing.
- Protects against duplicate concurrent analysis execution via per-job thread locking.
- Automatically resolves Module 4 analysis as a programmatic backend dependency.
- Persists aggregate analysis and event records to PostgreSQL.
- Serves product engagement, shelf interactions, comparison journeys, and reports.
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
from app.models.product_interaction import (
    ProductInteractionAnalysis,
    ProductInteractionEventModel,
)
from app.models.shelf import Shelf
from app.models.store import Store
from app.module5.engine import Module5InteractionEngine
from app.module5.report_generator import Module5ReportGenerator
from app.schemas.module5 import (
    InteractionEventItem,
    Module5AnalysisResponse,
    Module5ReportResponse,
    Module5SummarySchema,
    ProductComparisonItem,
    ProductEngagementItem,
    ShelfInteractionItem,
)
from app.services import module4_service

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
    m4_config_hash: str,
    db_products: List[Product],
    job_completed_at: Optional[Any] = None,
) -> str:
    """
    Compute a deterministic SHA-256 fingerprint for Module 5 inputs.
    Associates the analysis with:
    - AI Job ID
    - Store ID
    - Camera ID
    - Module 4 configuration fingerprint
    - Store product catalog entities (IDs, names, SKUs, shelf IDs)
    - Module 5 engine version
    """
    hasher = hashlib.sha256()
    hasher.update(str(job_id).encode("utf-8"))
    hasher.update(str(store_id).encode("utf-8"))
    hasher.update(str(camera_id).encode("utf-8"))
    hasher.update(m4_config_hash.encode("utf-8"))
    if job_completed_at:
        hasher.update(str(job_completed_at).encode("utf-8"))

    product_reprs = []
    for p in sorted(db_products, key=lambda x: str(x.id)):
        shelf_id = str(p.shelf_id) if p.shelf_id else ""
        product_reprs.append(f"{p.id}:{p.name}:{p.sku}:{shelf_id}")
    hasher.update("|".join(product_reprs).encode("utf-8"))

    hasher.update(b"m5_engine_v1.1")
    return hasher.hexdigest()


def _check_module3_outputs_exist(output_dir: Path) -> bool:
    """Verify that required Module 3 structured outputs exist on disk."""
    if not output_dir.exists():
        return False

    candidate_files = [
        output_dir / "phase5" / "reports" / "attention_events.json",
        output_dir / "phase5" / "attention_events.json",
        output_dir / "phase4" / "reports" / "zone_dwell_summary.json",
        output_dir / "phase4" / "zone_dwell_summary.json",
        output_dir / "phase3" / "reports" / "zone_visits.json",
        output_dir / "phase3" / "reports" / "paths.json",
        output_dir / "phase2" / "reports" / "tracks.json",
        output_dir / "reports" / "attention_events.json",
    ]
    return any(p.exists() for p in candidate_files)


def _build_analysis_response_from_db(
    db: Session,
    job: AIJob,
    existing_analysis: ProductInteractionAnalysis,
) -> Module5AnalysisResponse:
    """Build Module5AnalysisResponse directly from persisted PostgreSQL record."""
    summary_dict = existing_analysis.summary_data or {}
    summary_schema = Module5SummarySchema(**summary_dict)
    products_list = [
        ProductEngagementItem(**p) for p in (existing_analysis.product_metrics or [])
    ]
    shelves_list = [
        ShelfInteractionItem(**s) for s in (existing_analysis.shelf_metrics or [])
    ]
    comparisons_list = [
        ProductComparisonItem(**c)
        for c in (existing_analysis.comparison_patterns or [])
    ]

    event_count = (
        db.query(ProductInteractionEventModel)
        .filter(ProductInteractionEventModel.analysis_id == existing_analysis.id)
        .count()
    )

    return Module5AnalysisResponse(
        job_id=job.id,
        camera_id=job.camera_id,
        store_id=job.store_id,
        status="COMPLETED",
        summary=summary_schema,
        products=products_list,
        shelves=shelves_list,
        comparisons=comparisons_list,
        total_event_count=event_count,
    )


def get_module5_analysis(
    db: Session,
    job_id: uuid.UUID,
) -> Module5AnalysisResponse:
    """
    Pure READ-ONLY retrieval of existing Module 5 product interaction analysis.
    Guaranteed NEVER to execute the analysis engine or modify database/disk.
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

    existing_analysis = (
        db.query(ProductInteractionAnalysis)
        .filter(ProductInteractionAnalysis.job_id == job_id)
        .first()
    )
    if not existing_analysis or not existing_analysis.summary_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Module 5 product interaction analysis has not been generated for this job yet. Please click 'Run Analysis' or 'Re-evaluate'.",
        )

    return _build_analysis_response_from_db(db, job, existing_analysis)


def run_module5_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = True,
) -> Module5AnalysisResponse:
    """
    Explicitly execute Module 5 Product Interaction Engine on completed AI job outputs.
    Invoked only when user explicitly triggers 'Run Analysis' or 'Re-evaluate'.
    Persists new results to DB and disk, and returns the response.
    """
    return get_or_run_module5_analysis(db, job_id, force_rerun=force_rerun)


def get_or_run_module5_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = False,
) -> Module5AnalysisResponse:
    """
    Retrieve existing Module 5 analysis for a job, or run it on completed Module 3/4 outputs.
    
    Behavior:
    - If valid result already exists in DB with matching config hash and force_rerun=False:
      Returns stored result immediately without executing the analysis engine.
    - If force_rerun=True (user clicked "Re-evaluate"):
      Invalidates existing analysis, executes engine afresh under per-job lock,
      persists new results to DB and disk, and returns the updated analysis.
    - Automatically executes Module 4 as a backend dependency if not yet generated.
    - Protects against duplicate concurrent analysis execution.
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

    # 1. Calculate configuration fingerprint
    db_shelves = db.query(Shelf).filter(Shelf.store_id == job.store_id).all()
    db_products = db.query(Product).filter(Product.store_id == job.store_id).all()
    regions_file = project_root / "ai" / "configs" / "attention_regions.json"

    m4_hash = module4_service.compute_m4_config_hash(
        job_id=job.id,
        store_id=job.store_id,
        camera_id=job.camera_id,
        db_shelves=db_shelves,
        regions_file_path=regions_file if regions_file.exists() else None,
        job_completed_at=job.completed_at,
    )
    current_config_hash = compute_m5_config_hash(
        job_id=job.id,
        store_id=job.store_id,
        camera_id=job.camera_id,
        m4_config_hash=m4_hash,
        db_products=db_products,
        job_completed_at=job.completed_at,
    )

    # 2. Fast-path check: Return persisted result from DB if valid and not force_rerun
    if not force_rerun:
        existing_analysis = (
            db.query(ProductInteractionAnalysis)
            .filter(ProductInteractionAnalysis.job_id == job_id)
            .first()
        )
        if existing_analysis and existing_analysis.summary_data:
            stored_hash = existing_analysis.summary_data.get("config_hash")
            if stored_hash is None or stored_hash == current_config_hash:
                return _build_analysis_response_from_db(db, job, existing_analysis)

    # 3. Synchronized Execution under per-job lock (prevents duplicate simultaneous analysis)
    if not output_dir or not output_dir.exists() or not _check_module3_outputs_exist(output_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Required Module 3 data is unavailable.",
        )

    job_lock = _get_m5_job_lock(job_id)
    with job_lock:
        # Double check if another concurrent thread completed the analysis
        if not force_rerun:
            existing_analysis = (
                db.query(ProductInteractionAnalysis)
                .filter(ProductInteractionAnalysis.job_id == job_id)
                .first()
            )
            if existing_analysis and existing_analysis.summary_data:
                stored_hash = existing_analysis.summary_data.get("config_hash")
                if stored_hash is None or stored_hash == current_config_hash:
                    return _build_analysis_response_from_db(db, job, existing_analysis)

        # ── Backend Dependency: Auto-Generate Module 4 if Missing ────
        m4_report_file = output_dir / "module4" / "module4_attention_report.json"
        if not m4_report_file.exists() or force_rerun:
            logger.info(f"Module 5 triggering backend Module 4 dependency for job {job_id}")
            module4_service.get_or_run_module4_analysis(db, job_id, force_rerun=force_rerun)

        # ── Run Module 5 Engine on Completed Outputs ────────────────────
        shelf_regions: List[Dict[str, Any]] = []
        if regions_file.exists():
            try:
                with open(regions_file, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    shelf_regions.extend(cfg.get("regions", []))
            except Exception:
                pass

        # Enrich with DB shelf metadata
        for s in db_shelves:
            matched = False
            for r in shelf_regions:
                if (s.shelf_code and s.shelf_code == r.get("id")) or (
                    s.name and s.name.lower() == r.get("name", "").lower()
                ):
                    r["shelf_code"] = s.shelf_code
                    r["db_id"] = str(s.id)
                    r["shelf_id"] = str(s.id)
                    if s.zone:
                        r["zone_id"] = s.zone.name or str(s.zone.id)
                    matched = True
            if not matched:
                shelf_regions.append({
                    "id": s.shelf_code or str(s.id),
                    "shelf_id": str(s.id),
                    "shelf_code": s.shelf_code,
                    "name": s.name,
                    "shelf_name": s.name,
                    "type": "shelf",
                    "zone_id": s.zone.name if s.zone else "unknown",
                })

        product_list = [
            {
                "id": str(p.id),
                "product_id": str(p.id),
                "name": p.name,
                "product_name": p.name,
                "sku": p.sku,
                "shelf_id": str(p.shelf_id),
                "shelf_code": p.shelf.shelf_code if p.shelf else None,
                "shelf_name": p.shelf.name if p.shelf else "Unknown",
            }
            for p in db_products
        ]

        # Execute Module 5 Engine
        try:
            engine = Module5InteractionEngine()
            report_dict = engine.process_completed_job(
                job_output_dir=output_dir,
                configured_shelves=shelf_regions,
                configured_products=product_list,
                product_mappings=None,
                store_id=str(job.store_id),
                camera_id=str(job.camera_id),
                pos_transactions=None,
            )
        except Exception as exc:
            logger.error(f"Module 5 Product Interaction Engine execution failed for job {job_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Module 5 analysis failed: {str(exc)}. Retry available.",
            )

        summary_raw = report_dict.get("summary", {})
        products_raw = report_dict.get("products", [])
        shelves_raw = report_dict.get("shelves", [])
        comparisons_raw = report_dict.get("comparisons", [])
        events_raw = report_dict.get("events_sample", [])

        # Attach configuration signature and analyzed timestamp
        summary_raw["config_hash"] = current_config_hash
        summary_raw["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        summary_raw["version"] = "1.1"

        # 4. Persist or update in PostgreSQL
        analysis_record = (
            db.query(ProductInteractionAnalysis)
            .filter(ProductInteractionAnalysis.job_id == job.id)
            .first()
        )
        if not analysis_record:
            analysis_record = ProductInteractionAnalysis(
                id=uuid.uuid4(),
                job_id=job.id,
                camera_id=job.camera_id,
                store_id=job.store_id,
            )
            db.add(analysis_record)

        analysis_record.total_views = summary_raw.get("total_views", 0)
        analysis_record.total_pickups = summary_raw.get("total_pickups", 0)
        analysis_record.total_returns = summary_raw.get("total_returns", 0)
        analysis_record.total_comparisons = summary_raw.get("total_comparisons", 0)
        analysis_record.total_purchases = summary_raw.get("total_purchases", 0)
        analysis_record.total_unique_viewers = summary_raw.get("total_unique_viewers", 0)
        analysis_record.total_engagement_duration_sec = summary_raw.get(
            "total_engagement_duration_sec", 0.0
        )
        analysis_record.pickup_detection_status = summary_raw.get(
            "pickup_detection_status", "INSUFFICIENT_VISUAL_EVIDENCE"
        )
        analysis_record.purchase_data_status = summary_raw.get(
            "purchase_data_status", "UNAVAILABLE / NOT CONFIGURED (No POS Data)"
        )
        analysis_record.product_metrics = products_raw
        analysis_record.shelf_metrics = shelves_raw
        analysis_record.comparison_patterns = comparisons_raw
        analysis_record.summary_data = summary_raw

        # Clear old events if updating
        if analysis_record.id:
            db.query(ProductInteractionEventModel).filter(
                ProductInteractionEventModel.analysis_id == analysis_record.id
            ).delete()

        # Persist individual event records
        events_to_add = [
            ProductInteractionEventModel(
                id=uuid.uuid4(),
                analysis_id=analysis_record.id,
                job_id=job.id,
                event_id=ev.get("event_id") or f"EVT_{idx}",
                event_type=ev.get("event_type", "PRODUCT_VIEWED"),
                track_id=int(ev.get("track_id", 0)),
                session_id=ev.get("session_id"),
                product_id=ev.get("product_id"),
                product_name=ev.get("product_name"),
                sku=ev.get("sku"),
                shelf_id=ev.get("shelf_id"),
                shelf_name=ev.get("shelf_name"),
                camera_id=job.camera_id,
                store_id=job.store_id,
                timestamp=float(ev.get("timestamp", 0.0)),
                start_time=float(ev.get("start_time", 0.0)),
                end_time=(
                    float(ev.get("end_time", 0.0))
                    if ev.get("end_time") is not None
                    else None
                ),
                duration_seconds=float(ev.get("duration_seconds", 0.0)),
                confidence=float(ev.get("confidence", 0.8)),
                source=ev.get("source", "MODULE_4_ATTENTION"),
                metadata_json=ev.get("metadata"),
            )
            for idx, ev in enumerate(events_raw)
        ]
        if events_to_add:
            db.add_all(events_to_add)

        try:
            db.commit()
            db.refresh(analysis_record)
        except Exception:
            db.rollback()
            analysis_record = (
                db.query(ProductInteractionAnalysis)
                .filter(ProductInteractionAnalysis.job_id == job.id)
                .first()
            )
            if analysis_record:
                analysis_record.total_views = summary_raw.get("total_views", 0)
                analysis_record.total_pickups = summary_raw.get("total_pickups", 0)
                analysis_record.total_returns = summary_raw.get("total_returns", 0)
                analysis_record.total_comparisons = summary_raw.get("total_comparisons", 0)
                analysis_record.total_purchases = summary_raw.get("total_purchases", 0)
                analysis_record.total_unique_viewers = summary_raw.get("total_unique_viewers", 0)
                analysis_record.total_engagement_duration_sec = summary_raw.get(
                    "total_engagement_duration_sec", 0.0
                )
                analysis_record.product_metrics = products_raw
                analysis_record.shelf_metrics = shelves_raw
                analysis_record.comparison_patterns = comparisons_raw
                analysis_record.summary_data = summary_raw
                db.commit()
                db.refresh(analysis_record)

        summary_schema = Module5SummarySchema(**summary_raw)
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
            total_event_count=len(events_to_add),
        )


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


def get_product_comparisons(
    db: Session, job_id: uuid.UUID
) -> List[ProductComparisonItem]:
    """Retrieve observed multi-product consideration sequences (read-only)."""
    analysis = get_module5_analysis(db, job_id)
    return analysis.comparisons


def get_interaction_events(
    db: Session,
    job_id: uuid.UUID,
    track_id: Optional[int] = None,
    product_id: Optional[str] = None,
    shelf_id: Optional[str] = None,
    event_type: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> Tuple[List[InteractionEventItem], int]:
    """
    Retrieve granular interaction events with filtering and pagination (read-only).
    """
    query = db.query(ProductInteractionEventModel).filter(
        ProductInteractionEventModel.job_id == job_id
    )

    if track_id is not None:
        query = query.filter(ProductInteractionEventModel.track_id == track_id)
    if product_id is not None:
        query = query.filter(ProductInteractionEventModel.product_id == product_id)
    if shelf_id is not None:
        query = query.filter(ProductInteractionEventModel.shelf_id == shelf_id)
    if event_type is not None:
        query = query.filter(ProductInteractionEventModel.event_type == event_type)

    query = query.order_by(ProductInteractionEventModel.start_time.asc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    records = query.all()
    items = [
        InteractionEventItem(
            event_id=r.event_id,
            event_type=r.event_type,
            track_id=r.track_id,
            session_id=r.session_id,
            store_id=str(r.store_id) if r.store_id else None,
            camera_id=str(r.camera_id) if r.camera_id else None,
            product_id=r.product_id,
            product_name=r.product_name,
            sku=r.sku,
            shelf_id=r.shelf_id,
            shelf_name=r.shelf_name,
            timestamp=r.timestamp,
            start_time=r.start_time,
            end_time=r.end_time,
            duration_seconds=r.duration_seconds,
            confidence=r.confidence,
            source=r.source,
            metadata=r.metadata_json,
        )
        for r in records
    ]
    return items, total


def get_module5_report(db: Session, job_id: uuid.UUID) -> Module5ReportResponse:
    """Retrieve full JSON and Markdown report for Module 5 (read-only)."""
    analysis = get_module5_analysis(db, job_id)
    job = db.query(AIJob).filter(AIJob.id == job_id).first()

    project_root = _get_project_root()
    output_dir = None
    if job and job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    md_file = (
        output_dir / "module5" / "module5_interaction_report.md"
        if output_dir
        else None
    )
    json_file = (
        output_dir / "module5" / "module5_interaction_report.json"
        if output_dir
        else None
    )

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
        json_content = (
            analysis.model_dump()
            if hasattr(analysis, "model_dump")
            else analysis.dict()
        )

    if not md_content or not md_content.strip():
        report_gen = Module5ReportGenerator()
        md_content = report_gen.generate_markdown_report(json_content)
        if output_dir and output_dir.exists():
            try:
                m5_dir = output_dir / "module5"
                m5_dir.mkdir(parents=True, exist_ok=True)
                with open(
                    m5_dir / "module5_interaction_report.md", "w", encoding="utf-8"
                ) as f:
                    f.write(md_content)
            except Exception:
                pass

    return Module5ReportResponse(
        job_id=job_id,
        json_report=json_content,
        markdown_report=md_content,
    )
