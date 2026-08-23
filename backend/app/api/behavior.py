"""
Module 6 API
============
REST API endpoints for Consumer Behavior Intelligence Analysis.
Serves segment breakdowns, per-session classifications, journey timelines,
zone transition matrices, and funnel friction analytics.
"""

from typing import Any, Dict, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schemas.behavior import (
    Module6AnalysisResponse,
    Module6TriggerResponse,
    JourneyTimelineSchema,
    ZoneTransitionSchema,
    FunnelStageSchema,
)
from app.services import behavior_service

router = APIRouter(prefix="/api/behavior", tags=["Consumer Behavior (Module 6)"])
router_v1 = APIRouter(prefix="/api/v1/behavior", tags=["Consumer Behavior (Module 6)"])


@router.post("/{job_id}/analyze", response_model=Module6TriggerResponse)
@router_v1.post("/{job_id}/analyze", response_model=Module6TriggerResponse)
@router.post("/jobs/{job_id}/analyze", response_model=Module6TriggerResponse)
@router_v1.post("/jobs/{job_id}/analyze", response_model=Module6TriggerResponse)
def trigger_behavior_analysis(
    job_id: uuid.UUID,
    force_recompute: bool = False,
    db: Session = Depends(get_db),
):
    """
    Trigger or re-evaluate Module 6 consumer behavior analysis for a completed AI job.
    Uses cached analysis if available and `force_recompute` is False.
    """
    result = behavior_service.run_module6_analysis(
        job_id=job_id,
        db=db,
        force_recompute=force_recompute,
    )
    return Module6TriggerResponse(
        job_id=str(job_id),
        status="completed",
        summary=result.get("summary"),
    )


@router.get("/{job_id}/analysis", response_model=Module6AnalysisResponse)
@router_v1.get("/{job_id}/analysis", response_model=Module6AnalysisResponse)
@router.get("/jobs/{job_id}/analysis", response_model=Module6AnalysisResponse)
@router_v1.get("/jobs/{job_id}/analysis", response_model=Module6AnalysisResponse)
def get_behavior_analysis(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve the full Module 6 consumer behavior analysis result.
    Returns existing cached results, or generates and stores them on first visit.
    """
    return behavior_service.get_or_run_module6_analysis(job_id=job_id, db=db, force_recompute=False)


@router.get("/{job_id}/journeys", response_model=List[JourneyTimelineSchema])
@router_v1.get("/{job_id}/journeys", response_model=List[JourneyTimelineSchema])
@router.get("/jobs/{job_id}/journeys", response_model=List[JourneyTimelineSchema])
@router_v1.get("/jobs/{job_id}/journeys", response_model=List[JourneyTimelineSchema])
def get_journeys(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve all per-session journey timelines for a specific job.
    """
    result = behavior_service.get_or_run_module6_analysis(job_id=job_id, db=db, force_recompute=False)
    return result.get("journeys", [])


@router.get("/{job_id}/transitions")
@router_v1.get("/{job_id}/transitions")
@router.get("/jobs/{job_id}/transitions")
@router_v1.get("/jobs/{job_id}/transitions")
def get_transitions(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve the zone-to-zone Markov transition probability matrix.
    """
    result = behavior_service.get_or_run_module6_analysis(job_id=job_id, db=db, force_recompute=False)
    return result.get("zone_transitions", {})


@router.get("/{job_id}/funnel")
@router_v1.get("/{job_id}/funnel")
@router.get("/jobs/{job_id}/funnel")
@router_v1.get("/jobs/{job_id}/funnel")
def get_funnel(job_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Retrieve the shopper stage funnel and friction point analysis.
    """
    result = behavior_service.get_or_run_module6_analysis(job_id=job_id, db=db, force_recompute=False)
    return {
        "funnel": result.get("funnel", {}),
        "friction_points": result.get("friction_points", []),
    }


