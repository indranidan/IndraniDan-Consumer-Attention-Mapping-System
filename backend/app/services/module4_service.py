"""
Module 4 Service
==================
Business logic for Module 4 Attention Engine:
- Ingests completed Module 3 jobs without re-running YOLO or ByteTrack.
- Persists aggregate analysis and event records to PostgreSQL.
- Serves shelf engagement, product attention, events, reports, and heatmaps.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import uuid

# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.models.attention import AttentionAnalysis, AttentionEventModel
from app.models.camera import Camera
from app.models.product import Product
from app.models.shelf import Shelf
from app.models.store import Store
from app.module4.engine import Module4AttentionEngine
from app.module4.report_generator import Module4ReportGenerator
from app.schemas.module4 import (
    AttentionEventItem,
    Module4AnalysisResponse,
    Module4HeatmapResponse,
    Module4QualityMetrics,
    Module4ReportResponse,
    Module4SummarySchema,
    ProductMetricItem,
    ShelfMetricItem,
)


def _get_project_root() -> Path:
    """Determine the project root directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir.parent


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
    output_dir = (project_root / job.output_path).resolve() if job.output_path else None
    if not output_dir or not output_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job output directory does not exist.",
        )

    existing_analysis = db.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job_id).first()

    if existing_analysis and not force_rerun:
        # Load from DB
        summary_dict = existing_analysis.summary_data or {}
        summary_schema = Module4SummarySchema(**summary_dict)
        shelves_list = [ShelfMetricItem(**s) for s in (existing_analysis.shelf_metrics or [])]
        products_list = [ProductMetricItem(**p) for p in (existing_analysis.product_metrics or [])]
        quality_obj = (
            Module4QualityMetrics(**existing_analysis.quality_metrics)
            if existing_analysis.quality_metrics
            else None
        )

        # Load heatmap if exists
        heatmap_data = None
        m4_report_file = output_dir / "module4" / "module4_attention_report.json"
        if m4_report_file.exists():
            try:
                with open(m4_report_file, "r", encoding="utf-8") as f:
                    r_json = json.load(f)
                    heatmap_data = r_json.get("heatmap")
            except Exception:
                pass

        return Module4AnalysisResponse(
            job_id=job.id,
            camera_id=job.camera_id,
            store_id=job.store_id,
            status="COMPLETED",
            summary=summary_schema,
            shelves=shelves_list,
            products=products_list,
            quality_metrics=quality_obj,
            heatmap=heatmap_data,
        )

    # ── Run Module 4 Engine on Module 3 Outputs ───────────────────
    # 1. Fetch configured shelves from DB or attention_regions.json
    db_shelves = db.query(Shelf).filter(Shelf.store_id == job.store_id).all()
    shelf_regions = []

    # Read base attention_regions.json if available
    regions_file = project_root / "ai" / "configs" / "attention_regions.json"
    if regions_file.exists():
        try:
            with open(regions_file, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                shelf_regions.extend(cfg.get("regions", []))
        except Exception:
            pass

    # Enrich configured regions with DB shelf metadata if available
    for s in db_shelves:
        for r in shelf_regions:
            if (s.shelf_code and s.shelf_code == r.get("id")) or (s.name and s.name.lower() == r.get("name", "").lower()):
                r["shelf_code"] = s.shelf_code
                r["db_id"] = str(s.id)
                if s.zone:
                    r["zone_id"] = s.zone.zone_code or str(s.zone.id)

    # 2. Fetch products for store
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

    # 3. Execute Module 4 Engine
    engine = Module4AttentionEngine()
    report_dict = engine.process_completed_module3_job(
        job_output_dir=output_dir,
        shelf_regions=shelf_regions,
        product_mappings=None, # Spatial product polygon not yet configured for physical camera
        store_id=str(job.store_id),
        camera_id=str(job.camera_id),
    )

    summary_raw = report_dict.get("summary", {})
    shelves_raw = report_dict.get("shelves", [])
    products_raw = report_dict.get("products", []) or engine.product_detector.get_unconfigured_placeholder(product_list)
    quality_raw = report_dict.get("quality_metrics", {})
    heatmap_raw = report_dict.get("heatmap", {})

    # If products were not returned, use placeholder
    if not products_raw and product_list:
        products_raw = [p.to_dict() for p in engine.product_detector.get_unconfigured_placeholder(product_list)]

    # 4. Persist or update in database
    analysis_record = db.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job.id).first()
    if not analysis_record:
        analysis_record = AttentionAnalysis(
            id=uuid.uuid4(),
            job_id=job.id,
            camera_id=job.camera_id,
            store_id=job.store_id,
        )
        db.add(analysis_record)

    analysis_record.total_events = summary_raw.get("total_attention_events", 0)
    analysis_record.total_attention_duration_sec = summary_raw.get("total_attention_duration_sec", 0.0)
    analysis_record.average_attention_duration_sec = summary_raw.get("average_attention_duration_sec", 0.0)
    analysis_record.shelf_engagement_score_avg = summary_raw.get("shelf_engagement_score_avg", 0.0)
    analysis_record.shelf_metrics = shelves_raw
    analysis_record.product_metrics = [p if isinstance(p, dict) else p.to_dict() for p in products_raw]
    analysis_record.quality_metrics = quality_raw
    analysis_record.summary_data = summary_raw

    # Clear old events if updating
    if analysis_record.id:
        db.query(AttentionEventModel).filter(AttentionEventModel.analysis_id == analysis_record.id).delete()

    # Persist individual event records (up to 500 events)
    events_sample = report_dict.get("events_sample", [])
    events_to_add = [
        AttentionEventModel(
            id=uuid.uuid4(),
            analysis_id=analysis_record.id,
            job_id=job.id,
            track_id=int(ev.get("track_id", 0)),
            session_id=ev.get("session_id"),
            target_type=ev.get("target_type", "shelf"),
            target_id=str(ev.get("target_id", "unknown")),
            target_name=str(ev.get("target_name", "Unknown")),
            zone_id=str(ev.get("zone_id", "unknown")),
            start_time=float(ev.get("start_time", 0.0)),
            end_time=float(ev.get("end_time", 0.0)) if ev.get("end_time") is not None else None,
            duration_seconds=float(ev.get("duration_seconds", 0.0) or 0.0),
            attention_direction=str(ev.get("attention_direction", "UNKNOWN")),
            confidence=float(ev.get("confidence", 0.0)),
            visit_number=int(ev.get("visit_number", 1)),
        )
        for ev in events_sample
    ]
    if events_to_add:
        db.add_all(events_to_add)

    try:
        db.commit()
        db.refresh(analysis_record)
    except Exception:
        db.rollback()
        # Concurrently created by another worker/thread - re-fetch and update
        analysis_record = db.query(AttentionAnalysis).filter(AttentionAnalysis.job_id == job.id).first()
        if analysis_record:
            analysis_record.total_events = summary_raw.get("total_attention_events", 0)
            analysis_record.total_attention_duration_sec = summary_raw.get("total_attention_duration_sec", 0.0)
            analysis_record.average_attention_duration_sec = summary_raw.get("average_attention_duration_sec", 0.0)
            analysis_record.shelf_engagement_score_avg = summary_raw.get("shelf_engagement_score_avg", 0.0)
            analysis_record.shelf_metrics = shelves_raw
            analysis_record.product_metrics = [p if isinstance(p, dict) else p.to_dict() for p in products_raw]
            analysis_record.quality_metrics = quality_raw
            analysis_record.summary_data = summary_raw
            db.commit()
            db.refresh(analysis_record)

    summary_schema = Module4SummarySchema(**summary_raw)
    shelves_schema = [ShelfMetricItem(**s) for s in shelves_raw]
    products_schema = [ProductMetricItem(**(p if isinstance(p, dict) else p.to_dict())) for p in products_raw]
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


def get_shelf_metrics(db: Session, job_id: uuid.UUID) -> List[ShelfMetricItem]:
    """Retrieve shelf metrics for a completed job."""
    analysis = get_or_run_module4_analysis(db, job_id)
    return analysis.shelves


def get_product_metrics(db: Session, job_id: uuid.UUID) -> List[ProductMetricItem]:
    """Retrieve product metrics for a completed job."""
    analysis = get_or_run_module4_analysis(db, job_id)
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
    Retrieve granular attention events with optional filters.
    """
    # Ensure analysis exists
    get_or_run_module4_analysis(db, job_id)

    query = db.query(AttentionEventModel).filter(AttentionEventModel.job_id == job_id)

    if track_id is not None:
        query = query.filter(AttentionEventModel.track_id == track_id)
    if target_id is not None:
        query = query.filter(AttentionEventModel.target_id == target_id)
    if target_type is not None:
        query = query.filter(AttentionEventModel.target_type == target_type)

    query = query.order_by(AttentionEventModel.start_time.asc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    records = query.all()
    items = [
        AttentionEventItem(
            event_id=str(r.id),
            track_id=r.track_id,
            session_id=r.session_id,
            camera_id=None,
            store_id=None,
            timestamp=r.start_time,
            start_time=r.start_time,
            end_time=r.end_time,
            duration_seconds=r.duration_seconds,
            attention_type="SHELF_ATTENTION" if r.target_type == "shelf" else "HEAD_POSE_ATTENTION",
            target_type=r.target_type,
            target_id=r.target_id,
            target_name=r.target_name,
            zone_id=r.zone_id,
            attention_direction=r.attention_direction,
            confidence=r.confidence,
            status="completed",
            visit_number=r.visit_number,
        )
        for r in records
    ]
    return items, total


def get_module4_report(db: Session, job_id: uuid.UUID) -> Module4ReportResponse:
    """Retrieve full JSON and Markdown report for Module 4."""
    analysis = get_or_run_module4_analysis(db, job_id)
    job = db.query(AIJob).filter(AIJob.id == job_id).first()

    project_root = _get_project_root()
    output_dir = (project_root / job.output_path).resolve() if (job and job.output_path) else None
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

    # Generate markdown report dynamically if file was missing or empty
    if not md_content or not md_content.strip():
        report_gen = Module4ReportGenerator()
        md_content = report_gen.generate_markdown_report(json_content)
        # Attempt to save to disk for future requests if output directory is available
        if output_dir and output_dir.exists():
            try:
                m4_dir = output_dir / "module4"
                m4_dir.mkdir(parents=True, exist_ok=True)
                with open(m4_dir / "module4_attention_report.md", "w", encoding="utf-8") as f:
                    f.write(md_content)
            except Exception:
                pass

    return Module4ReportResponse(
        job_id=job_id,
        json_report=json_content,
        markdown_report=md_content,
    )



def get_module4_heatmap(db: Session, job_id: uuid.UUID) -> Module4HeatmapResponse:
    """Retrieve camera-space attention heatmap data."""
    analysis = get_or_run_module4_analysis(db, job_id)
    heatmap_dict = analysis.heatmap or {
        "camera_width": 1280,
        "camera_height": 720,
        "total_points": 0,
        "points": [],
    }

    image_url = f"/api/ai/results/{job_id}/files/module4/attention_heatmap.png"

    return Module4HeatmapResponse(
        job_id=job_id,
        camera_width=heatmap_dict.get("camera_width", 1280),
        camera_height=heatmap_dict.get("camera_height", 720),
        total_points=heatmap_dict.get("total_points", 0),
        points=heatmap_dict.get("points", []),
        image_url=image_url,
    )
