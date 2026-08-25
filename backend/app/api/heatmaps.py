"""
Module 7 — Heatmap API Routes
================================
REST endpoints for store-wide, shelf-level, traffic flow,
and job-specific spatial heatmap analytics.

Endpoints:
    GET    /api/heatmaps/store/{store_id}         Store-wide attention heatmap
    GET    /api/heatmaps/shelf/{shelf_id}          Shelf vertical & horizontal gaze
    GET    /api/heatmaps/traffic/{store_id}        Customer traffic flow density
    GET    /api/heatmaps/job/{job_id}              Job-level heatmap + diagnostics
    GET    /api/heatmaps/job/{job_id}/image        Pre-rendered heatmap PNG image
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.core.dependencies import any_role
from app.services.heatmap_service import (
    get_store_heatmap,
    get_shelf_heatmap,
    get_traffic_heatmap,
    get_job_heatmap,
)

router = APIRouter(prefix="/api/heatmaps", tags=["Heatmaps (Module 7)"])


@router.get(
    "/store/{store_id}",
    summary="Get store-wide attention heatmap",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Store not found"},
    },
)
def store_heatmap(
    store_id: uuid.UUID,
    colormap: str = Query("JET", description="Colormap name: JET, TURBO, INFERNO, VIRIDIS"),
    sigma: float = Query(8.0, ge=1.0, le=50.0, description="Gaussian kernel sigma"),
    response: Response = None,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated store-wide attention heatmap data by merging
    attention coordinates across all completed AI jobs for the store.
    """
    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    result = get_store_heatmap(store_id, db, colormap=colormap.upper(), sigma=sigma)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/shelf/{shelf_id}",
    summary="Get shelf vertical & horizontal gaze heatmap",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Shelf not found"},
    },
)
def shelf_heatmap(
    shelf_id: uuid.UUID,
    response: Response = None,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Returns shelf-level vertical tier gaze distribution (Top, Eye-Level,
    Reach, Bottom) and horizontal planogram attention spread.
    """
    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    result = get_shelf_heatmap(shelf_id, db)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/traffic/{store_id}",
    summary="Get customer traffic flow density map",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Store not found"},
    },
)
def traffic_heatmap(
    store_id: uuid.UUID,
    response: Response = None,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Returns customer traffic flow density, path lines, and velocity vectors
    computed from Module 3 shopper tracking trajectories.
    """
    if response:
        response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"

    result = get_traffic_heatmap(store_id, db)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/job/{job_id}",
    summary="Get job-level heatmap with shelf tiers and hotspot diagnostics",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "AI job not found"},
    },
)
def job_heatmap(
    job_id: uuid.UUID,
    colormap: str = Query("JET", description="Colormap name"),
    sigma: float = Query(8.0, ge=1.0, le=50.0, description="Gaussian kernel sigma"),
    response: Response = None,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Returns detailed heatmap for a single AI job including attention density,
    shelf vertical tier analysis, and hotspot/dead-zone diagnostics.
    """
    if response:
        response.headers["Cache-Control"] = "public, max-age=20, stale-while-revalidate=40"

    result = get_job_heatmap(job_id, db, colormap=colormap.upper(), sigma=sigma)
    if result.get("error"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result["error"])
    return result


@router.get(
    "/job/{job_id}/image",
    summary="Get pre-rendered heatmap PNG image for a job",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Image not found"},
    },
)
def job_heatmap_image(
    job_id: uuid.UUID,
    colormap: str = Query("JET", description="Colormap name"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Returns a pre-rendered colormapped PNG heatmap image for the specified job.
    Generates on-the-fly if not already cached on disk.
    """
    import sys
    from app.models.ai_job import AIJob
    from app.repositories.ai_document_repository import AIDocumentRepository

    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")

    # Check for existing rendered image
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    image_dir = project_root / "outputs" / "ai_jobs" / str(job_id) / "heatmaps"
    image_path = image_dir / f"heatmap_{colormap.lower()}.png"

    if image_path.exists():
        return FileResponse(str(image_path), media_type="image/png")

    # Generate on the fly
    m4_doc = AIDocumentRepository.get_module4_analysis_sync(str(job_id))
    m4_data = m4_doc if isinstance(m4_doc, dict) else {}
    heatmap_data = m4_data.get("heatmap", {})
    points = heatmap_data.get("points", [])
    cam_w = heatmap_data.get("camera_width", 1280)
    cam_h = heatmap_data.get("camera_height", 720)

    if not points:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No attention data available for heatmap image rendering.",
        )

    # Normalize and compute
    _pr = str(project_root)
    if _pr not in sys.path:
        sys.path.insert(0, _pr)
    from ai.attention_analysis.heatmap_engine import (
        normalize_camera_coords,
        compute_density_matrix,
        render_heatmap_image,
    )

    normalized = normalize_camera_coords(points, cam_w, cam_h)
    matrix = compute_density_matrix(normalized)
    rendered = render_heatmap_image(matrix, image_path, colormap=colormap.upper(), width=cam_w, height=cam_h)

    if rendered and rendered.exists():
        return FileResponse(str(rendered), media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Failed to generate heatmap image.",
    )
