"""
Module 8 Service
==================
Business logic for Module 8 Product Attractiveness Scoring Engine:
- Ingests Module 3 tracking, Module 4 attention, and Module 5 interaction data.
- Idempotent analysis execution with deterministic configuration hashing.
- Protects against duplicate concurrent execution via per-job thread locking.
- Persists aggregate scoring results to MongoDB with disk fallback.
- Serves score cards, leaderboards, and intelligence reports.
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
from app.models.product import Product
from app.models.shelf import Shelf
from app.modules.scoring.engine import Module8ScoringEngine
from app.modules.scoring.report_generator import Module8ReportGenerator
from app.repositories.ai_document_repository import AIDocumentRepository
from app.schemas.scoring import (
    LeaderboardItem,
    Module8AnalysisResponse,
    Module8LeaderboardResponse,
    Module8ReportResponse,
    Module8SummarySchema,
    ProductScoreCardItem,
)
from app.services import attention_service as module4_service

logger = logging.getLogger("module8_service")

# ── Per-Job Concurrency Locks ──────────────────────────────────────
_m8_locks: Dict[str, threading.Lock] = {}
_m8_global_lock = threading.Lock()


def _get_m8_job_lock(job_id: uuid.UUID) -> threading.Lock:
    """Retrieve or create a thread-safe mutex for the specific AI job."""
    key = str(job_id)
    with _m8_global_lock:
        if key not in _m8_locks:
            _m8_locks[key] = threading.Lock()
        return _m8_locks[key]


def _get_project_root() -> Path:
    """Determine the project root directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir.parent


def compute_m8_config_hash(
    job_id: uuid.UUID,
    store_id: uuid.UUID,
    camera_id: uuid.UUID,
    db_products: List[Product],
    db_shelves: List[Shelf],
    m4_analysis_timestamp: Optional[str] = None,
    m5_analysis_timestamp: Optional[str] = None,
    job_completed_at: Optional[datetime] = None,
) -> str:
    """
    Compute a deterministic SHA-256 hash of all configuration and upstream inputs
    that govern Module 8 Product Attractiveness Scoring.
    """
    hasher = hashlib.sha256()

    hasher.update(str(job_id).encode("utf-8"))
    hasher.update(str(store_id).encode("utf-8"))
    hasher.update(str(camera_id).encode("utf-8"))
    hasher.update(b"module8_v1")

    products_repr = sorted(
        [
            f"{p.id}:{p.name}:{p.sku}:{p.shelf_id}:{getattr(p, 'category', '')}:{getattr(p, 'price', 0.0)}"
            for p in db_products
        ]
    )
    hasher.update(";".join(products_repr).encode("utf-8"))

    shelves_repr = sorted(
        [
            f"{s.id}:{s.shelf_code}:{s.name}:{s.zone_id}:{getattr(s, 'category', '')}"
            for s in db_shelves
        ]
    )
    hasher.update(";".join(shelves_repr).encode("utf-8"))

    if m4_analysis_timestamp:
        hasher.update(m4_analysis_timestamp.encode("utf-8"))
    if m5_analysis_timestamp:
        hasher.update(m5_analysis_timestamp.encode("utf-8"))

    return hasher.hexdigest()


def _build_analysis_response_from_dict(
    job: AIJob,
    analysis_dict: Dict[str, Any],
) -> Module8AnalysisResponse:
    """Construct Module8AnalysisResponse schema from MongoDB/disk analysis dict."""
    summary_raw = analysis_dict.get("summary", {})
    products_raw = analysis_dict.get("products", [])

    summary_schema = Module8SummarySchema(
        total_products_scored=summary_raw.get("total_products_scored", 0),
        average_attractiveness_score=summary_raw.get("average_attractiveness_score", 0.0),
        top_performer_id=summary_raw.get("top_performer_id"),
        top_performer_name=summary_raw.get("top_performer_name"),
        top_performer_score=summary_raw.get("top_performer_score", 0.0),
        bottom_performer_id=summary_raw.get("bottom_performer_id"),
        bottom_performer_name=summary_raw.get("bottom_performer_name"),
        bottom_performer_score=summary_raw.get("bottom_performer_score", 0.0),
        average_confidence=summary_raw.get("average_confidence", 0.0),
        config_hash=summary_raw.get("config_hash"),
        analyzed_at=summary_raw.get("analyzed_at"),
        version=summary_raw.get("version", "1.0"),
    )

    products_schema = [ProductScoreCardItem(**p) for p in products_raw]

    return Module8AnalysisResponse(
        job_id=job.id,
        camera_id=job.camera_id,
        store_id=job.store_id,
        status="COMPLETED",
        summary=summary_schema,
        products=products_schema,
        total_products_scored=len(products_raw),
    )


# ── MongoDB / Memory Persistence Helpers ───────────────────────────

_MODULE8_COLLECTION = "module8_scoring"
_m8_memory_store: Dict[str, Any] = {}


def _save_m8_analysis(job_id: uuid.UUID, analysis_data: Dict[str, Any]) -> bool:
    """Save Module 8 scoring analysis to MongoDB with memory fallback."""
    job_id_str = str(job_id)
    doc = {
        "job_id": job_id_str,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis_data,
    }
    _m8_memory_store[job_id_str] = doc

    try:
        from app.database.mongodb import get_sync_mongo_db
        db = get_sync_mongo_db()
        if db is not None:
            db[_MODULE8_COLLECTION].update_one(
                {"job_id": job_id_str},
                {"$set": doc},
                upsert=True,
            )
    except Exception as exc:
        logger.warning(f"MongoDB save failed for Module 8 (job {job_id_str}): {exc}")

    return True


def _get_m8_analysis(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve Module 8 analysis from MongoDB or memory fallback."""
    try:
        from app.database.mongodb import get_sync_mongo_db
        db = get_sync_mongo_db()
        if db is not None:
            doc = db[_MODULE8_COLLECTION].find_one({"job_id": job_id}, {"_id": 0})
            if doc:
                return doc.get("analysis")
    except Exception:
        pass
    mem_doc = _m8_memory_store.get(job_id)
    return mem_doc.get("analysis") if mem_doc else None


# ── Public Service Functions ───────────────────────────────────────

def get_module8_scores(db: Session, job_id: uuid.UUID) -> Module8AnalysisResponse:
    """
    Retrieve existing Module 8 scoring results for a job.
    If no analysis has been executed yet or configuration has changed, runs it on demand.
    """
    return get_or_run_module8_analysis(db, job_id, force_rerun=False)


def get_or_run_module8_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = False,
) -> Module8AnalysisResponse:
    """
    Retrieve existing Module 8 scoring or run it on completed job data.
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

    current_config_hash = compute_m8_config_hash(
        job_id=job.id,
        store_id=job.store_id,
        camera_id=job.camera_id,
        db_products=db_products,
        db_shelves=db_shelves,
        job_completed_at=job.completed_at,
    )

    # 2. Fast-path: Return persisted result if valid
    if not force_rerun:
        existing = _get_m8_analysis(str(job_id))
        if existing and existing.get("summary"):
            stored_hash = existing.get("summary", {}).get("config_hash")
            if stored_hash is None or stored_hash == current_config_hash:
                return _build_analysis_response_from_dict(job, existing)

    # 3. Synchronized Execution under per-job lock
    job_lock = _get_m8_job_lock(job_id)
    with job_lock:
        # Double-check after acquiring lock
        if not force_rerun:
            existing = _get_m8_analysis(str(job_id))
            if existing and existing.get("summary"):
                stored_hash = existing.get("summary", {}).get("config_hash")
                if stored_hash is None or stored_hash == current_config_hash:
                    return _build_analysis_response_from_dict(job, existing)

        product_list = [
            {
                "id": str(p.id),
                "name": p.name,
                "sku": p.sku,
                "shelf_id": str(p.shelf_id),
                "category": getattr(p, "category", None),
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
                "category": getattr(s, "category", None),
            }
            for s in db_shelves
        ]

        try:
            engine = Module8ScoringEngine()
            result = engine.process_completed_job(
                job_output_dir=output_dir or Path("."),
                configured_products=product_list,
                configured_shelves=shelf_list,
                store_id=str(job.store_id),
                camera_id=str(job.camera_id),
            )
        except Exception as exc:
            logger.error(f"Module 8 Scoring Engine failed for job {job_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Module 8 scoring failed: {str(exc)}. Retry available.",
            )

        summary_raw = result.get("summary", {})
        products_raw = result.get("products", [])

        summary_raw["config_hash"] = current_config_hash
        summary_raw["analyzed_at"] = datetime.now(timezone.utc).isoformat()

        analysis_dict = {
            "summary": summary_raw,
            "products": products_raw,
        }

        # Persist to MongoDB
        _save_m8_analysis(job.id, analysis_dict)

        # Write reports to disk cache
        if output_dir:
            try:
                m8_dir = output_dir / "module8"
                m8_dir.mkdir(parents=True, exist_ok=True)

                report_gen = Module8ReportGenerator()
                json_report = report_gen.generate_json_report(
                    summary=result.get("scored_profiles", []) and engine._build_summary(result["scored_profiles"]) or __import__("app.modules.scoring.models", fromlist=["Module8Summary"]).Module8Summary(),
                    products=result.get("scored_profiles", []),
                    job_metadata={
                        "store_id": str(job.store_id),
                        "camera_id": str(job.camera_id),
                        "job_id": str(job.id),
                    },
                )
                report_gen.save_reports(json_report, m8_dir)
            except Exception as file_exc:
                logger.warning(f"Failed to write Module 8 disk artifacts: {file_exc}")

        return _build_analysis_response_from_dict(job, analysis_dict)


def run_module8_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = True,
) -> Module8AnalysisResponse:
    """Explicitly execute Module 8 Scoring Engine."""
    return get_or_run_module8_analysis(db, job_id, force_rerun=force_rerun)


def get_scoring_leaderboard(
    db: Session,
    job_id: uuid.UUID,
    top_n: int = 5,
) -> Module8LeaderboardResponse:
    """Retrieve top/bottom performer leaderboard for a job."""
    analysis = get_module8_scores(db, job_id)

    sorted_products = sorted(
        analysis.products,
        key=lambda p: p.attractiveness_score,
        reverse=True,
    )

    top_items = []
    for rank, p in enumerate(sorted_products[:top_n], 1):
        top_items.append(LeaderboardItem(
            rank=rank,
            product_id=p.product_id,
            product_name=p.product_name,
            sku=p.sku,
            attractiveness_score=p.attractiveness_score,
            rating=p.rating,
            confidence_level=p.confidence.confidence_level,
            intrinsic_attractiveness_score=p.intrinsic_attractiveness_score,
        ))

    bottom_items = []
    for rank, p in enumerate(reversed(sorted_products[-top_n:]), 1):
        bottom_items.append(LeaderboardItem(
            rank=rank,
            product_id=p.product_id,
            product_name=p.product_name,
            sku=p.sku,
            attractiveness_score=p.attractiveness_score,
            rating=p.rating,
            confidence_level=p.confidence.confidence_level,
            intrinsic_attractiveness_score=p.intrinsic_attractiveness_score,
        ))

    return Module8LeaderboardResponse(
        job_id=job_id,
        top_performers=top_items,
        bottom_performers=bottom_items,
        total_products_scored=analysis.total_products_scored,
    )


def get_scoring_report(
    db: Session,
    job_id: uuid.UUID,
) -> Module8ReportResponse:
    """Generate or retrieve structured JSON and Markdown scoring report."""
    analysis = get_module8_scores(db, job_id)

    from app.modules.scoring.models import Module8Summary as M8Sum
    summary = M8Sum(
        total_products_scored=analysis.summary.total_products_scored,
        average_attractiveness_score=analysis.summary.average_attractiveness_score,
        top_performer_id=analysis.summary.top_performer_id,
        top_performer_name=analysis.summary.top_performer_name,
        top_performer_score=analysis.summary.top_performer_score,
        bottom_performer_id=analysis.summary.bottom_performer_id,
        bottom_performer_name=analysis.summary.bottom_performer_name,
        bottom_performer_score=analysis.summary.bottom_performer_score,
        average_confidence=analysis.summary.average_confidence,
    )

    report_gen = Module8ReportGenerator()
    json_report = report_gen.generate_json_report(summary, [])
    # Re-insert the already-serialized products from analysis
    json_report["products"] = [p.model_dump() for p in analysis.products]
    md_report = report_gen.generate_markdown_report(json_report)

    return Module8ReportResponse(
        job_id=job_id,
        json_report=json_report,
        markdown_report=md_report,
    )
