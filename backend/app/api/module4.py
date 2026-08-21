"""
Module 4 — Attention Analysis API Routes
==========================================
REST endpoints for Module 4 Attention Analysis Engine.

Endpoints:
    GET    /api/module4/jobs/{job_id}/attention-analysis   Get full Module 4 analysis results
    GET    /api/module4/jobs/{job_id}/shelf-metrics        Get shelf engagement metrics
    GET    /api/module4/jobs/{job_id}/product-metrics      Get product attention metrics
    GET    /api/module4/jobs/{job_id}/events               Get attention events log
    GET    /api/module4/jobs/{job_id}/report               Get JSON & Markdown attention reports
    GET    /api/module4/jobs/{job_id}/heatmap              Get camera attention heatmap data
    POST   /api/module4/jobs/{job_id}/run                  Trigger/Refresh Module 4 analysis
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.dependencies import admin_or_store_manager, any_role
from app.database.database import get_db
from app.models.user import User
from app.schemas.module4 import (
    AttentionEventItem,
    Module4AnalysisResponse,
    Module4HeatmapResponse,
    Module4ReportResponse,
    ProductMetricItem,
    ShelfMetricItem,
)
from app.services import module4_service

router = APIRouter(prefix="/api/module4", tags=["Module 4 — Attention Analysis"])


@router.get(
    "/jobs/{job_id}/attention-analysis",
    response_model=Module4AnalysisResponse,
    summary="Get full Module 4 attention analysis results (read-only)",
    responses={
        404: {"description": "Job not found or analysis not generated yet"},
        400: {"description": "Job is not completed yet"},
    },
)
def get_attention_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Retrieve existing Module 4 attention analysis results for a completed AI job.
    Pure read-only operation; does NOT trigger analysis engine execution.
    """
    return module4_service.get_module4_analysis(db, job_id)


@router.get(
    "/jobs/{job_id}/shelf-metrics",
    response_model=List[ShelfMetricItem],
    summary="Get shelf engagement metrics",
)
def get_shelf_metrics(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve detailed shelf engagement metrics for a job."""
    return module4_service.get_shelf_metrics(db, job_id)


@router.get(
    "/jobs/{job_id}/product-metrics",
    response_model=List[ProductMetricItem],
    summary="Get product attention metrics",
)
def get_product_metrics(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve product focus metrics for a job (or not configured note)."""
    return module4_service.get_product_metrics(db, job_id)


@router.get(
    "/jobs/{job_id}/events",
    response_model=List[AttentionEventItem],
    summary="Get granular attention events",
)
def get_attention_events(
    job_id: uuid.UUID,
    response: Response,
    track_id: Optional[int] = Query(default=None, description="Filter by ByteTrack ID"),
    target_id: Optional[str] = Query(default=None, description="Filter by target ID"),
    target_type: Optional[str] = Query(default=None, description="Filter by target type (shelf, product, zone)"),
    page: Optional[int] = Query(default=None, ge=1, description="Page number"),
    page_size: Optional[int] = Query(default=None, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List structured attention events with optional filters."""
    items, total = module4_service.get_attention_events(
        db,
        job_id=job_id,
        track_id=track_id,
        target_id=target_id,
        target_type=target_type,
        page=page,
        page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/jobs/{job_id}/report",
    response_model=Module4ReportResponse,
    summary="Get Module 4 structured report",
)
def get_attention_report(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve structured JSON and Markdown reports for Module 4."""
    return module4_service.get_module4_report(db, job_id)


@router.get(
    "/jobs/{job_id}/heatmap",
    response_model=Module4HeatmapResponse,
    summary="Get camera attention heatmap data",
)
def get_attention_heatmap(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve 2D camera-space attention heatmap coordinates and image URL."""
    return module4_service.get_module4_heatmap(db, job_id)


@router.post(
    "/jobs/{job_id}/run",
    response_model=Module4AnalysisResponse,
    summary="Run or refresh Module 4 analysis on completed job",
)
def run_module4_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Explicitly trigger or re-evaluate Module 4 Attention Engine on an existing completed Module 3 job."""
    return module4_service.run_module4_analysis(db, job_id, force_rerun=True)
