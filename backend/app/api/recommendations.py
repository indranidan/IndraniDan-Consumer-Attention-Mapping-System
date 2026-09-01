"""
Module 9 — Recommendation & Optimization API Routes
=====================================================
REST endpoints for Module 9 Prescriptive Merchandising Recommendations:
- GET  /api/v1/recommendations                  (Store or global recommendations)
- GET  /api/v1/recommendations/jobs/{job_id}    (Job-level recommendations)
- POST /api/v1/recommendations/jobs/{job_id}/run (Trigger/Refresh recommendations)
- POST /api/v1/recommendations/simulate         (What-If planogram simulation)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import admin_or_store_manager, any_role
from app.database.database import get_db
from app.models.user import User
from app.schemas.recommendation import (
    PlanogramSimulationRequestSchema,
    PlanogramSimulationResponse,
    RecommendationResponse,
    StoreRecommendationResponse,
)
from app.services import recommendation_service as module9_service

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendation & Optimization Engine"])


@router.get(
    "",
    response_model=StoreRecommendationResponse,
    summary="Get recommendations by store",
)
def get_store_recommendations(
    store_id: uuid.UUID = Query(..., description="Store ID to aggregate recommendations for"),
    category: Optional[str] = Query(default=None, description="Filter by RecommendationCategory"),
    priority: Optional[str] = Query(default=None, description="Filter by RecommendationPriority"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve aggregated merchandising recommendations across recent completed jobs for a store."""
    return module9_service.get_recommendations_by_store(
        db, store_id=store_id, category=category, priority=priority
    )


@router.get(
    "/jobs/{job_id}",
    response_model=RecommendationResponse,
    summary="Get recommendations for a specific AI job",
    responses={
        404: {"description": "Job not found"},
        400: {"description": "Job is not completed yet"},
    },
)
def get_job_recommendations(
    job_id: uuid.UUID,
    category: Optional[str] = Query(default=None, description="Filter by RecommendationCategory"),
    priority: Optional[str] = Query(default=None, description="Filter by RecommendationPriority"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve full categorized, priority-ranked recommendations for a completed AI job."""
    return module9_service.get_recommendations(
        db, job_id=job_id, category=category, priority=priority
    )


@router.post(
    "/jobs/{job_id}/run",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger/Refresh Module 9 recommendations",
)
def run_job_recommendations(
    job_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Force re-computation of recommendations for a completed AI job."""
    res = module9_service.run_module9_analysis(db, job_id, force_rerun=True)
    return module9_service.get_recommendations(db, job_id)


@router.post(
    "/simulate",
    response_model=PlanogramSimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run interactive What-If planogram simulation",
)
def simulate_planogram_change(
    payload: PlanogramSimulationRequestSchema,
    current_user: User = Depends(any_role),
):
    """
    Stateless counterfactual simulation of a shelf tier relocation or facing adjustment.
    Returns projected visibility score, attractiveness adjustments, and estimated % lifts.
    """
    return module9_service.run_simulation(payload.model_dump())
