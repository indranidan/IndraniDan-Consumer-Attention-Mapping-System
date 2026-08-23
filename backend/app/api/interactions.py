"""
Module 5 — Product Interaction Analysis API Routes
===================================================
REST endpoints for Module 5 Product Interaction Analysis Engine.

Endpoints:
    GET    /api/module5/jobs/{job_id}/interaction-analysis   Get full Module 5 analysis results
    GET    /api/module5/jobs/{job_id}/product-engagement      Get product engagement matrix
    GET    /api/module5/jobs/{job_id}/shelf-interactions     Get shelf interaction metrics
    GET    /api/module5/jobs/{job_id}/events                 Get granular interaction events log
    GET    /api/module5/jobs/{job_id}/comparisons            Get observed comparison patterns
    GET    /api/module5/jobs/{job_id}/report                 Get JSON & Markdown interaction reports
    POST   /api/module5/jobs/{job_id}/run                    Trigger/Refresh Module 5 analysis
"""

import uuid
from typing import List, Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query, Response, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.dependencies import admin_or_store_manager, any_role
from app.database.database import get_db
# pyrefly: ignore [missing-import]
from app.models.user import User
from app.schemas.interaction import (
    InteractionEventItem,
    Module5AnalysisResponse,
    Module5ReportResponse,
    ProductComparisonItem,
    ProductEngagementItem,
    ShelfInteractionItem,
)
from app.services import interaction_service as module5_service

router = APIRouter(prefix="/api/v1/interactions", tags=["Product Interaction Analysis"])


@router.get(
    "/jobs/{job_id}/interaction-analysis",
    response_model=Module5AnalysisResponse,
    summary="Get full Module 5 product interaction analysis results (read-only)",
    responses={
        404: {"description": "Job not found or analysis not generated yet"},
        400: {"description": "Job is not completed yet"},
    },
)
def get_interaction_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Retrieve Module 5 product interaction analysis results for a completed AI job.
    Returns existing cached results, or generates and stores them on first visit.
    """
    return module5_service.get_or_run_module5_analysis(db, job_id, force_rerun=False)


@router.get(
    "/jobs/{job_id}/product-engagement",
    response_model=List[ProductEngagementItem],
    summary="Get product engagement matrix",
)
def get_product_engagement(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve per-product engagement metrics for a job."""
    return module5_service.get_product_engagement(db, job_id)


@router.get(
    "/jobs/{job_id}/shelf-interactions",
    response_model=List[ShelfInteractionItem],
    summary="Get shelf interaction metrics",
)
def get_shelf_interactions(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve shelf interaction metrics for a job."""
    return module5_service.get_shelf_interactions(db, job_id)


@router.get(
    "/jobs/{job_id}/events",
    response_model=List[InteractionEventItem],
    summary="Get granular interaction events",
)
def get_interaction_events(
    job_id: uuid.UUID,
    response: Response,
    track_id: Optional[int] = Query(default=None, description="Filter by ByteTrack ID"),
    product_id: Optional[str] = Query(default=None, description="Filter by product ID"),
    shelf_id: Optional[str] = Query(default=None, description="Filter by shelf ID"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type (PRODUCT_VIEWED, PRODUCT_PICKED_UP, PRODUCT_RETURNED, PRODUCT_COMPARED, PRODUCT_PURCHASED)"),
    page: Optional[int] = Query(default=None, ge=1, description="Page number"),
    page_size: Optional[int] = Query(default=None, ge=1, le=200, description="Items per page"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List structured product interaction events with optional filters."""
    items, total = module5_service.get_interaction_events(
        db,
        job_id=job_id,
        track_id=track_id,
        product_id=product_id,
        shelf_id=shelf_id,
        event_type=event_type,
        page=page,
        page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/jobs/{job_id}/comparisons",
    response_model=List[ProductComparisonItem],
    summary="Get observed multi-product consideration sequences",
)
def get_product_comparisons(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve observed multi-product consideration journeys and comparison patterns."""
    return module5_service.get_product_comparisons(db, job_id)


@router.get(
    "/jobs/{job_id}/report",
    response_model=Module5ReportResponse,
    summary="Get Module 5 structured report",
)
def get_interaction_report(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve structured JSON and Markdown reports for Module 5."""
    return module5_service.get_module5_report(db, job_id)


@router.post(
    "/jobs/{job_id}/run",
    response_model=Module5AnalysisResponse,
    summary="Run or refresh Module 5 analysis on completed job",
)
def run_module5_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Explicitly trigger or re-evaluate Module 5 Product Interaction Engine on an existing completed AI job."""
    return module5_service.run_module5_analysis(db, job_id, force_rerun=True)
