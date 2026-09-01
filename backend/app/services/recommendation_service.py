"""
Module 9 Service
==================
Business logic for Module 9 Recommendation & Optimization Engine:
- Aggregates telemetry from Module 8 scoring, Module 7 heatmaps, Module 6 behavior
- Runs the Module9RecommendationEngine to generate prioritized recommendations
- Persists results to MongoDB with in-memory fallback
- Serves recommendations, filters, and planogram simulations
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.ai_job import AIJob
from app.modules.recommendation.engine import Module9RecommendationEngine
from app.modules.recommendation.models import (
    PlanogramSimulationRequest,
)
from app.modules.recommendation.simulator import PlanogramSimulator

logger = logging.getLogger("module9_service")


# ── MongoDB / Memory Persistence ──────────────────────────────

_MODULE9_COLLECTION = "module9_recommendations"
_m9_memory_store: Dict[str, Any] = {}


def _save_m9_analysis(job_id: uuid.UUID, analysis_data: Dict[str, Any]) -> bool:
    """Save Module 9 recommendations to MongoDB with memory fallback."""
    job_id_str = str(job_id)
    doc = {
        "job_id": job_id_str,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "analysis": analysis_data,
    }
    _m9_memory_store[job_id_str] = doc

    try:
        from app.database.mongodb import get_sync_mongo_db
        db = get_sync_mongo_db()
        if db is not None:
            db[_MODULE9_COLLECTION].update_one(
                {"job_id": job_id_str},
                {"$set": doc},
                upsert=True,
            )
    except Exception as exc:
        logger.warning(f"MongoDB save failed for Module 9 (job {job_id_str}): {exc}")

    return True


def _get_m9_analysis(job_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve Module 9 recommendations from MongoDB or memory fallback."""
    try:
        from app.database.mongodb import get_sync_mongo_db
        db = get_sync_mongo_db()
        if db is not None:
            doc = db[_MODULE9_COLLECTION].find_one({"job_id": job_id}, {"_id": 0})
            if doc:
                return doc.get("analysis")
    except Exception:
        pass
    mem_doc = _m9_memory_store.get(job_id)
    return mem_doc.get("analysis") if mem_doc else None


# ── Telemetry Aggregation Helpers ─────────────────────────────

def _get_module8_product_profiles(db: Session, job_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieve Module 8 scored product profiles for a job."""
    try:
        from app.services.scoring_service import get_or_run_module8_analysis
        result = get_or_run_module8_analysis(db, job_id, force_rerun=False)
        if result and hasattr(result, "products"):
            return [
                p.model_dump() if hasattr(p, "model_dump") else p.dict() if hasattr(p, "dict") else p
                for p in result.products
            ]
    except Exception as exc:
        logger.warning(f"Could not retrieve Module 8 profiles for job {job_id}: {exc}")
    return []


def _get_heatmap_data(db: Session, job_id: uuid.UUID, store_id: Optional[uuid.UUID] = None) -> Optional[Dict[str, Any]]:
    """Retrieve Module 7 heatmap data for layout rules."""
    try:
        from app.services.heatmap_service import get_job_heatmap, get_store_heatmap
        result = get_job_heatmap(job_id, db)
        if not result or result.get("error"):
            if store_id:
                result = get_store_heatmap(store_id, db)
        if result and not result.get("error"):
            return result
    except Exception as exc:
        logger.debug(f"Heatmap data not available for job {job_id}: {exc}")
    return None


def _get_behavior_data(db: Session, job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Retrieve Module 6 behavior data for layout rules."""
    try:
        from app.services.behavior_service import get_or_run_module6_analysis
        result = get_or_run_module6_analysis(job_id=job_id, db=db, force_recompute=False)
        if result:
            return result if isinstance(result, dict) else (
                result.model_dump() if hasattr(result, "model_dump") else {}
            )
    except Exception as exc:
        logger.debug(f"Behavior data not available for job {job_id}: {exc}")
    return None


# ── Public Service Functions ──────────────────────────────────

def get_recommendations(
    db: Session,
    job_id: uuid.UUID,
    category: Optional[str] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve or generate Module 9 recommendations for a completed AI job.

    Returns cached results if available; otherwise runs the recommendation engine.
    Supports optional filtering by category and priority.
    """
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="AI job not found")
    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job has not completed yet")

    # Check cached results
    cached = _get_m9_analysis(str(job_id))
    if not cached:
        cached = _run_recommendation_analysis(db, job_id, job)

    # Apply filters
    recommendations = cached.get("recommendations", [])
    if category:
        recommendations = [r for r in recommendations if r.get("category") == category]
    if priority:
        recommendations = [r for r in recommendations if r.get("priority") == priority]

    return {
        "job_id": str(job_id),
        "store_id": str(job.store_id) if job.store_id else None,
        "recommendations": recommendations,
        "summary": cached.get("summary", {}),
        "total": len(recommendations),
    }


def get_recommendations_by_store(
    db: Session,
    store_id: uuid.UUID,
    category: Optional[str] = None,
    priority: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Aggregate recommendations across all completed jobs for a store.
    """
    jobs = (
        db.query(AIJob)
        .filter(AIJob.store_id == store_id, AIJob.status == "COMPLETED")
        .order_by(AIJob.completed_at.desc())
        .limit(5)
        .all()
    )

    all_recs: List[Dict[str, Any]] = []
    for job in jobs:
        try:
            result = get_recommendations(db, job.id, category=category, priority=priority)
            all_recs.extend(result.get("recommendations", []))
        except Exception:
            continue

    return {
        "store_id": str(store_id),
        "recommendations": all_recs,
        "total": len(all_recs),
        "jobs_analyzed": len(jobs),
    }


def run_simulation(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run a What-If planogram simulation.

    Stateless — no database mutations.
    """
    req = PlanogramSimulationRequest(
        product_id=request_data.get("product_id", ""),
        current_shelf_tier=request_data.get("current_shelf_tier", "UNKNOWN"),
        target_shelf_tier=request_data.get("target_shelf_tier", "UNKNOWN"),
        current_facing_count=request_data.get("current_facing_count", 1),
        target_facing_count=request_data.get("target_facing_count", 1),
        current_attractiveness_score=request_data.get("current_attractiveness_score", 0.0),
        current_intrinsic_score=request_data.get("current_intrinsic_score", 0.0),
    )
    result = PlanogramSimulator.simulate(req)
    return result.to_dict()


def run_module9_analysis(
    db: Session,
    job_id: uuid.UUID,
    force_rerun: bool = False,
) -> Dict[str, Any]:
    """
    Trigger or re-trigger Module 9 recommendation generation.
    """
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="AI job not found")
    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job has not completed yet")

    if not force_rerun:
        cached = _get_m9_analysis(str(job_id))
        if cached:
            return cached

    return _run_recommendation_analysis(db, job_id, job)


# ── Internal Analysis Runner ─────────────────────────────────

def _run_recommendation_analysis(
    db: Session, job_id: uuid.UUID, job: AIJob
) -> Dict[str, Any]:
    """Run the full Module 9 recommendation pipeline and persist results."""
    logger.info(f"Running Module 9 recommendation analysis for job {job_id}")

    # Gather telemetry from upstream modules
    product_profiles = _get_module8_product_profiles(db, job_id)
    heatmap_data = _get_heatmap_data(db, job_id, store_id=job.store_id)
    behavior_data = _get_behavior_data(db, job_id)

    # Run recommendation engine
    engine = Module9RecommendationEngine()
    result = engine.generate_recommendations(
        product_profiles=product_profiles,
        heatmap_data=heatmap_data,
        behavior_data=behavior_data,
        store_id=str(job.store_id) if job.store_id else None,
    )

    # Persist results
    _save_m9_analysis(job_id, result)
    logger.info(
        f"Module 9 generated {result['summary']['total_recommendations']} "
        f"recommendations for job {job_id}"
    )

    return result
