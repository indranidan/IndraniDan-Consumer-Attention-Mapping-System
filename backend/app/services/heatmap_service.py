"""
Module 7 — Heatmap Service
============================
Business logic for multi-job spatial aggregation, shelf vertical tier analysis,
traffic flow computation, and hotspot diagnostics.
Includes thread-safe in-memory TTL caching.
"""

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.store import Store
from app.models.shelf import Shelf
from app.models.camera import Camera
from app.models.ai_job import AIJob
from app.repositories.ai_document_repository import AIDocumentRepository
from app.modules.heatmap.shelf_heatmap import compute_full_shelf_heatmap
from app.modules.heatmap.traffic_heatmap import (
    compute_path_density,
    density_to_sparse_json,
    compute_traffic_flow_summary,
)
from app.modules.heatmap.hotspot_engine import compute_hotspot_diagnostics

logger = logging.getLogger("module7.heatmap_service")

# ── In-Memory TTL Cache ───────────────────────────────────────
_heatmap_cache: Dict[str, Any] = {}
_cache_lock = threading.Lock()
_CACHE_TTL_SEC = 30.0


def _cache_get(key: str) -> Optional[Any]:
    with _cache_lock:
        entry = _heatmap_cache.get(key)
        if entry and (time.time() - entry["ts"]) < _CACHE_TTL_SEC:
            return entry["data"]
        elif entry:
            del _heatmap_cache[key]
    return None


def _cache_set(key: str, data: Any) -> None:
    with _cache_lock:
        _heatmap_cache[key] = {"data": data, "ts": time.time()}


def invalidate_heatmap_cache(prefix: Optional[str] = None) -> None:
    """Invalidate heatmap cache entries. If prefix given, only matching keys."""
    with _cache_lock:
        if prefix:
            keys = [k for k in _heatmap_cache if k.startswith(prefix)]
            for k in keys:
                del _heatmap_cache[k]
        else:
            _heatmap_cache.clear()


# ── Store-Wide Heatmap ────────────────────────────────────────

def get_store_heatmap(
    store_id: uuid.UUID,
    db: Session,
    colormap: str = "JET",
    sigma: float = 8.0,
) -> Dict[str, Any]:
    """
    Generate a store-wide attention heatmap by aggregating Module 4
    attention data across all completed AI jobs for the store.
    """
    cache_key = f"store_heatmap:{store_id}:{colormap}:{sigma}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        return {"error": "Store not found", "store_id": str(store_id)}

    # Get all completed jobs for this store
    completed_jobs = (
        db.query(AIJob)
        .filter(AIJob.store_id == store_id, AIJob.status == "COMPLETED")
        .all()
    )

    if not completed_jobs:
        return _empty_store_heatmap(str(store_id), store.name)

    # Aggregate attention data from all jobs
    job_ids = [str(j.id) for j in completed_jobs]
    m4_batch = AIDocumentRepository.get_batch_module4_analyses_sync(job_ids)

    all_points = []
    for job_id_str, m4_doc in m4_batch.items():
        heatmap_data = m4_doc.get("heatmap", {})
        points = heatmap_data.get("points", [])
        cam_w = heatmap_data.get("camera_width", 1280)
        cam_h = heatmap_data.get("camera_height", 720)

        # Normalize to [0,1] space
        for pt in points:
            x = pt.get("x", 0)
            y = pt.get("y", 0)
            weight = pt.get("weight", 1.0)
            all_points.append({
                "nx": round(x / max(cam_w, 1), 6),
                "ny": round(y / max(cam_h, 1), 6),
                "weight": round(float(weight), 4),
                "target_id": pt.get("target_id"),
                "target_name": pt.get("target_name"),
            })

    # Compute density grid
    import sys
    _project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from ai.attention_analysis.heatmap_engine import (
        compute_density_matrix,
        density_matrix_to_json,
    )

    matrix = compute_density_matrix(all_points, sigma=sigma)
    grid_json = density_matrix_to_json(matrix)

    result = {
        "store_id": str(store_id),
        "store_name": store.name,
        "grid": grid_json,
        "metadata": {
            "grid_width": 200,
            "grid_height": 150,
            "total_input_points": len(all_points),
            "sigma": sigma,
            "colormap": colormap,
            "intensity_threshold": 0.0,
        },
        "total_cameras": len(set(j.camera_id for j in completed_jobs)),
        "total_jobs_aggregated": len(completed_jobs),
        "image_url": None,
    }

    _cache_set(cache_key, result)
    return result


# ── Shelf-Level Heatmap ───────────────────────────────────────

def get_shelf_heatmap(
    shelf_id: uuid.UUID,
    db: Session,
) -> Dict[str, Any]:
    """
    Generate a shelf-level vertical + horizontal gaze heatmap.
    """
    cache_key = f"shelf_heatmap:{shelf_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        return {"error": "Shelf not found", "shelf_id": str(shelf_id)}

    # Find all completed jobs for the shelf's store
    completed_jobs = (
        db.query(AIJob)
        .filter(AIJob.store_id == shelf.store_id, AIJob.status == "COMPLETED")
        .all()
    )

    job_ids = [str(j.id) for j in completed_jobs]
    m4_batch = AIDocumentRepository.get_batch_module4_analyses_sync(job_ids)

    # Collect gaze points targeting this shelf
    gaze_points = []
    for job_id_str, m4_doc in m4_batch.items():
        heatmap_data = m4_doc.get("heatmap", {})
        for pt in heatmap_data.get("points", []):
            if pt.get("target_id") == str(shelf_id) or pt.get("target_name") == shelf.name:
                gaze_points.append({
                    "x": pt.get("x", 0),
                    "y": pt.get("y", 0),
                    "weight": pt.get("weight", 1.0),
                })

    result = compute_full_shelf_heatmap(
        gaze_points=gaze_points,
        shelf_id=str(shelf_id),
        shelf_name=shelf.name,
    )

    _cache_set(cache_key, result)
    return result


# ── Traffic Flow ──────────────────────────────────────────────

def get_traffic_heatmap(
    store_id: uuid.UUID,
    db: Session,
) -> Dict[str, Any]:
    """
    Generate traffic flow density map from Module 3 tracking trajectories.
    """
    cache_key = f"traffic_heatmap:{store_id}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        return {"error": "Store not found", "store_id": str(store_id)}

    # Get trajectories from completed jobs via disk/MongoDB
    completed_jobs = (
        db.query(AIJob)
        .filter(AIJob.store_id == store_id, AIJob.status == "COMPLETED")
        .all()
    )

    all_trajectories = []
    for job in completed_jobs:
        # Try to load M3 path data from MongoDB or disk
        import json
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        output_dir = project_root / "outputs" / "ai_jobs" / str(job.id)
        for cand in [
            output_dir / "phase3" / "reports" / "paths.json",
            output_dir / "phase2" / "reports" / "tracks.json",
        ]:
            if cand.exists():
                try:
                    with open(cand, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and "paths" in data:
                        for track_id, path in data["paths"].items():
                            all_trajectories.append({"tracking_id": track_id, "path": path})
                    elif isinstance(data, list):
                        all_trajectories.extend(data)
                    break
                except Exception as e:
                    logger.warning(f"Error reading trajectory file {cand}: {e}")

    density_result = compute_path_density(all_trajectories)
    matrix = density_result["density_matrix"]
    cells = density_to_sparse_json(matrix)
    flow_summary = compute_traffic_flow_summary(all_trajectories)

    result = {
        "store_id": str(store_id),
        "store_name": store.name,
        "grid": {
            "grid_width": density_result["metadata"]["grid_width"],
            "grid_height": density_result["metadata"]["grid_height"],
            "max_intensity": density_result["metadata"]["max_density"],
            "total_cells": len(cells),
            "cells": cells,
        },
        "flow_vectors": density_result["flow_vectors"],
        "summary": flow_summary,
        "metadata": density_result["metadata"],
    }

    _cache_set(cache_key, result)
    return result


# ── Job-Level Heatmap ─────────────────────────────────────────

def get_job_heatmap(
    job_id: uuid.UUID,
    db: Session,
    colormap: str = "JET",
    sigma: float = 8.0,
) -> Dict[str, Any]:
    """
    Generate detailed heatmap analysis for a single AI job.
    Includes attention density, shelf vertical tiers, and hotspot diagnostics.
    """
    cache_key = f"job_heatmap:{job_id}:{colormap}:{sigma}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        return {"error": "Job not found", "job_id": str(job_id)}

    m4_doc = AIDocumentRepository.get_module4_analysis_sync(str(job_id))
    m4_data = m4_doc if isinstance(m4_doc, dict) else {}

    heatmap_data = m4_data.get("heatmap", {})
    points = heatmap_data.get("points", [])
    cam_w = heatmap_data.get("camera_width", 1280)
    cam_h = heatmap_data.get("camera_height", 720)

    # Normalize all points
    normalized = []
    for pt in points:
        normalized.append({
            "nx": round(pt.get("x", 0) / max(cam_w, 1), 6),
            "ny": round(pt.get("y", 0) / max(cam_h, 1), 6),
            "weight": round(float(pt.get("weight", 1.0)), 4),
            "target_id": pt.get("target_id"),
            "target_name": pt.get("target_name"),
        })

    import sys
    _project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from ai.attention_analysis.heatmap_engine import (
        compute_density_matrix,
        density_matrix_to_json,
    )

    matrix = compute_density_matrix(normalized, sigma=sigma)
    grid_json = density_matrix_to_json(matrix)

    # Shelf vertical heatmaps for shelves referenced in attention events
    shelf_heatmaps = []
    shelves_map = {}
    for pt in points:
        tid = pt.get("target_id")
        tname = pt.get("target_name", "")
        if tid and tid not in shelves_map:
            shelves_map[tid] = {"id": tid, "name": tname, "points": []}
        if tid:
            shelves_map[tid]["points"].append(pt)

    for sid, shelf_data in shelves_map.items():
        shelf_result = compute_full_shelf_heatmap(
            gaze_points=shelf_data["points"],
            shelf_id=sid,
            shelf_name=shelf_data["name"],
        )
        shelf_heatmaps.append(shelf_result)

    # Hotspot diagnostics (attention + empty traffic/interaction for single job)
    hotspot_result = compute_hotspot_diagnostics(
        attention_points=normalized,
        traffic_points=normalized,  # Use attention as proxy for single-camera traffic
        interaction_points=[],
    )

    result = {
        "job_id": str(job_id),
        "store_id": str(job.store_id) if job.store_id else "",
        "camera_id": str(job.camera_id) if job.camera_id else "",
        "grid": grid_json,
        "shelf_heatmaps": shelf_heatmaps,
        "hotspot_diagnostics": {
            "store_id": str(job.store_id) if job.store_id else "",
            "store_name": "",
            "zones": hotspot_result["zones"],
            "summary": hotspot_result["summary"],
            "grid_cols": hotspot_result["grid_meta"]["grid_cols"],
            "grid_rows": hotspot_result["grid_meta"]["grid_rows"],
        },
        "metadata": {
            "grid_width": 200,
            "grid_height": 150,
            "total_input_points": len(normalized),
            "sigma": sigma,
            "colormap": colormap,
            "intensity_threshold": 0.0,
        },
        "image_url": None,
    }

    _cache_set(cache_key, result)
    return result


# ── Helpers ───────────────────────────────────────────────────

def _empty_store_heatmap(store_id: str, store_name: str) -> Dict[str, Any]:
    return {
        "store_id": store_id,
        "store_name": store_name,
        "grid": {
            "grid_width": 200,
            "grid_height": 150,
            "max_intensity": 0.0,
            "total_cells": 0,
            "cells": [],
        },
        "metadata": {
            "grid_width": 200,
            "grid_height": 150,
            "total_input_points": 0,
            "sigma": 8.0,
            "colormap": "JET",
            "intensity_threshold": 0.0,
        },
        "total_cameras": 0,
        "total_jobs_aggregated": 0,
        "image_url": None,
    }
