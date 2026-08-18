"""
AI Job Routes
===============
REST endpoints for AI analysis job management.

Endpoints:
    POST   /api/ai/jobs                         Create and start AI analysis
    GET    /api/ai/jobs                         List AI jobs
    GET    /api/ai/jobs/{job_id}                Get job details
    POST   /api/ai/jobs/{job_id}/stop           Stop a running job
    GET    /api/ai/jobs/{job_id}/results        Get detailed results
    GET    /api/ai/results/{job_id}/video       Stream annotated video
    GET    /api/ai/results/{job_id}/files/{path} Serve output file
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.ai_job import (
    AIJobCreate,
    AIJobResponse,
    AIJobResultsResponse,
)
from app.schemas.auth import MessageResponse
from app.core.dependencies import admin_or_store_manager, any_role
from app.services import ai_job_service

router = APIRouter(prefix="/api/ai", tags=["AI Analytics"])


@router.post(
    "/jobs",
    response_model=AIJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and start AI analysis job",
    responses={
        404: {"description": "Camera or store not found"},
        400: {"description": "Camera not active, mismatch, or invalid source"},
        429: {"description": "Maximum concurrent jobs reached"},
    },
)
def create_ai_job(
    store_id: uuid.UUID = Form(...),
    camera_id: uuid.UUID = Form(...),
    input_type: str = Form("VIDEO_FILE"),
    source_override: str | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """
    Create a new AI analysis job for a store & camera.
    Supports VIDEO_FILE uploads and WEBCAM recordings.
    The analysis runs in the background — this endpoint returns immediately.
    Requires Administrator or Store Manager role.
    """
    payload = AIJobCreate(
        store_id=store_id,
        camera_id=camera_id,
        input_type=input_type,
        source_override=source_override,
    )
    return ai_job_service.create_job(db, payload, current_user, upload_file=file)


@router.get(
    "/jobs",
    response_model=list[AIJobResponse],
    summary="List AI jobs",
)
def list_ai_jobs(
    response: Response,
    store_id: uuid.UUID | None = Query(default=None, description="Filter by store ID"),
    camera_id: uuid.UUID | None = Query(default=None, description="Filter by camera ID"),
    status_filter: str | None = Query(
        default=None,
        alias="status",
        description="Filter by status (QUEUED, RUNNING, COMPLETED, FAILED, STOPPED)",
    ),
    page: int | None = Query(default=None, ge=1, description="Page number"),
    page_size: int | None = Query(default=None, ge=1, le=50, description="Items per page"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List AI analysis jobs. Available to all authenticated users."""
    items, total = ai_job_service.get_jobs(
        db,
        store_id=store_id,
        camera_id=camera_id,
        job_status=status_filter,
        page=page,
        page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/jobs/{job_id}",
    response_model=AIJobResponse,
    summary="Get AI job details",
    responses={404: {"description": "Job not found"}},
)
def get_ai_job(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a single AI job by ID. Available to all authenticated users."""
    return ai_job_service.get_job(db, job_id)


@router.post(
    "/jobs/{job_id}/stop",
    response_model=AIJobResponse,
    summary="Stop a running AI job",
    responses={
        404: {"description": "Job not found"},
        400: {"description": "Job cannot be stopped"},
    },
)
def stop_ai_job(
    job_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Stop a running or queued AI job. Requires Administrator or Store Manager role."""
    return ai_job_service.request_stop(db, job_id)


@router.get(
    "/jobs/{job_id}/results",
    response_model=AIJobResultsResponse,
    summary="Get AI job results",
    responses={404: {"description": "Job not found"}},
)
def get_ai_job_results(
    job_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Get detailed results for a completed AI job.
    Includes summary analytics, full report data, and available output files.
    """
    return ai_job_service.get_job_results(db, job_id)


@router.get(
    "/results/{job_id}/files/{file_path:path}",
    summary="Serve job output file",
    responses={
        404: {"description": "Job or file not found"},
        400: {"description": "Job not completed or invalid path"},
    },
)
def serve_ai_output_file(
    job_id: uuid.UUID,
    file_path: str,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Serve a specific output file from a completed AI job.
    Supports videos, images, JSON reports, and markdown files.
    Path traversal is prevented.
    """
    resolved_path = ai_job_service.get_job_output_file(db, job_id, file_path)

    # Determine media type
    suffix = resolved_path.suffix.lower()
    media_types = {
        ".mp4": "video/mp4",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".json": "application/json",
        ".md": "text/markdown",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".csv": "text/csv",
        ".txt": "text/plain",
        ".log": "text/plain",
    }
    media_type = media_types.get(suffix, "application/octet-stream")

    return FileResponse(
        path=str(resolved_path),
        media_type=media_type,
        filename=resolved_path.name,
    )
