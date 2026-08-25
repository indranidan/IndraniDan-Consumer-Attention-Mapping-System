"""
Module 8 — Product Attractiveness Scoring API Routes
======================================================
REST endpoints for Module 8 Product Attractiveness Scoring Engine.

Endpoints:
    GET    /api/v1/scoring/jobs/{job_id}/scores       Get full Module 8 scoring results
    GET    /api/v1/scoring/jobs/{job_id}/leaderboard   Get top/bottom performer leaderboard
    GET    /api/v1/scoring/jobs/{job_id}/report        Get JSON & Markdown scoring reports
    POST   /api/v1/scoring/jobs/{job_id}/run           Trigger/Refresh Module 8 scoring
"""

import uuid

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query, status
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session

from app.core.dependencies import admin_or_store_manager, any_role
from app.database.database import get_db
from app.models.user import User
from app.schemas.scoring import (
    Module8AnalysisResponse,
    Module8LeaderboardResponse,
    Module8ReportResponse,
)
from app.services import scoring_service as module8_service

router = APIRouter(prefix="/api/v1/scoring", tags=["Product Attractiveness Scoring"])


@router.get(
    "/jobs/{job_id}/scores",
    response_model=Module8AnalysisResponse,
    summary="Get full Module 8 product attractiveness scoring results",
    responses={
        404: {"description": "Job not found or scoring not generated yet"},
        400: {"description": "Job is not completed yet"},
    },
)
def get_scoring_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Retrieve Module 8 product attractiveness scoring results for a completed AI job.
    Returns existing cached results, or generates and stores them on first visit.
    """
    return module8_service.get_module8_scores(db, job_id)


@router.get(
    "/jobs/{job_id}/leaderboard",
    response_model=Module8LeaderboardResponse,
    summary="Get top/bottom performer leaderboard",
)
def get_scoring_leaderboard(
    job_id: uuid.UUID,
    top_n: int = Query(default=5, ge=1, le=20, description="Number of top/bottom items"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve top and bottom performer product leaderboards for a job."""
    return module8_service.get_scoring_leaderboard(db, job_id, top_n=top_n)


@router.get(
    "/jobs/{job_id}/report",
    response_model=Module8ReportResponse,
    summary="Get structured JSON & Markdown scoring report",
)
def get_scoring_report(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Generate or retrieve the full Module 8 scoring intelligence report."""
    return module8_service.get_scoring_report(db, job_id)


@router.post(
    "/jobs/{job_id}/run",
    response_model=Module8AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger/Refresh Module 8 scoring analysis",
    responses={
        404: {"description": "Job not found"},
        400: {"description": "Job is not completed yet"},
    },
)
def run_scoring_analysis(
    job_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """
    Force re-computation of Module 8 scoring for a completed AI job.
    Re-ingests Module 3/4/5 telemetry and recomputes all 5-pillar scores.
    """
    return module8_service.run_module8_analysis(db, job_id, force_rerun=True)
