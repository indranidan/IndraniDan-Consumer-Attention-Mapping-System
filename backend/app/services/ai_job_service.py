"""
AI Job Service
===============
Business logic for AI job management: creation, retrieval, result loading.
"""

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile, status

from app.models.ai_job import AIJob
from app.models.camera import Camera
from app.models.store import Store
from app.models.user import User
from app.schemas.ai_job import (
    AIJobCreate,
    AIJobReportResponse,
    AIJobResponse,
    AIJobResultsResponse,
)
from app.services.ai_worker import run_pipeline, stop_job as worker_stop_job, get_running_job_count
from app.core.config import get_settings


def _get_project_root() -> Path:
    """Determine the project root directory."""
    backend_dir = Path(__file__).resolve().parent.parent.parent
    return backend_dir.parent


def _to_response(job: AIJob) -> AIJobResponse:
    """Convert an AIJob ORM object to an AIJobResponse schema."""
    return AIJobResponse(
        id=job.id,
        camera_id=job.camera_id,
        store_id=job.store_id,
        input_type=job.input_type or "VIDEO_FILE",
        source=job.source,
        status=job.status,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message,
        output_path=job.output_path,
        summary=job.summary,
        zone_config=job.zone_config,
        created_by=job.created_by,
        created_at=job.created_at,
        updated_at=job.updated_at,
        camera_name=job.camera.name if job.camera else "",
        store_name=job.store.name if job.store else "",
        creator_name=job.creator.full_name if job.creator else "",
    )


def create_job(
    db: Session,
    payload: AIJobCreate,
    current_user: User,
    upload_file: UploadFile | None = None,
) -> AIJobResponse:
    """
    Create and start a new AI analysis job.

    Validates:
        - Store must exist (404)
        - Camera must exist (404)
        - Camera must belong to selected store (400)
        - Camera must be active (400)
        - Input type must be supported (400)
        - Video file or webcam source must be valid (400)
        - Concurrent job limit not exceeded (429)

    Returns the created job with QUEUED status.
    The background worker is launched immediately.
    """
    settings = get_settings()
    project_root = _get_project_root()

    # 1. Validate Store
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{payload.store_id}' not found.",
        )

    # 2. Validate Camera
    camera = db.query(Camera).filter(Camera.id == payload.camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id '{payload.camera_id}' not found.",
        )

    # 3. Validate Camera belongs to Store
    if camera.store_id != payload.store_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Selected camera does not belong to the selected store.",
        )

    if camera.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Camera '{camera.name}' is not active (status: {camera.status}).",
        )

    # 4. Validate Input Type
    input_type = (payload.input_type or "VIDEO_FILE").upper()
    if input_type not in ("VIDEO_FILE", "WEBCAM", "FUTURE_CAMERA"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported input type '{input_type}'. Supported options: VIDEO_FILE, WEBCAM.",
        )

    if input_type == "FUTURE_CAMERA":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Live camera input is not configured yet.",
        )

    # 5. Check Concurrent Job Limit
    running_count = get_running_job_count()
    if running_count >= settings.AI_MAX_CONCURRENT_JOBS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maximum concurrent AI jobs ({settings.AI_MAX_CONCURRENT_JOBS}) reached. "
                   f"Please wait for a running job to complete.",
        )

    job_id = uuid.uuid4()
    source: str = ""

    # 6. Resolve Input Source
    if input_type == "VIDEO_FILE":
        if upload_file:
            allowed_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
            file_ext = Path(upload_file.filename).suffix.lower() if upload_file.filename else ".mp4"
            if file_ext not in allowed_exts:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported video format '{file_ext}'. Allowed formats: {', '.join(sorted(allowed_exts))}",
                )

            input_dir = project_root / settings.AI_INPUT_PATH
            input_dir.mkdir(parents=True, exist_ok=True)
            saved_path = input_dir / f"{job_id}{file_ext}"

            # Stream chunks to prevent loading full file into memory
            with open(saved_path, "wb") as buffer:
                while chunk := upload_file.file.read(1024 * 1024):
                    buffer.write(chunk)

            source = str(saved_path)
        elif payload.source_override and payload.source_override.strip():
            source = payload.source_override.strip()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please select a video file.",
            )

    elif input_type == "WEBCAM":
        if upload_file:
            input_dir = project_root / settings.AI_INPUT_PATH
            input_dir.mkdir(parents=True, exist_ok=True)
            file_ext = Path(upload_file.filename).suffix.lower() if upload_file.filename else ".webm"
            saved_path = input_dir / f"{job_id}_webcam{file_ext}"

            with open(saved_path, "wb") as buffer:
                while chunk := upload_file.file.read(1024 * 1024):
                    buffer.write(chunk)

            source = str(saved_path)
        elif payload.source_override and payload.source_override.strip():
            source = payload.source_override.strip()
        else:
            source = str(settings.WEBCAM_DEVICE)

    if not source:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select Video File or Webcam as the analysis source.",
        )

    output_base = project_root / settings.AI_OUTPUT_PATH / str(job_id)

    # 7. Create Job Record
    job = AIJob(
        id=job_id,
        camera_id=camera.id,
        store_id=store.id,
        input_type=input_type,
        source=source,
        status="QUEUED",
        output_path=str(Path(settings.AI_OUTPUT_PATH) / str(job_id)),
        zone_config=payload.zone_config,
        created_by=current_user.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(job)
    db.commit()
    db.refresh(job)

    # 8. Launch Background Worker
    worker_thread = threading.Thread(
        target=run_pipeline,
        args=(job_id, source, str(output_base), settings.AI_PIPELINE_TIMEOUT, payload.zone_config),
        daemon=True,
        name=f"ai-worker-{job_id}",
    )
    worker_thread.start()

    return _to_response(job)


def get_job(
    db: Session,
    job_id: uuid.UUID,
) -> AIJobResponse:
    """Get a single AI job by ID."""
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI job with id '{job_id}' not found.",
        )
    return _to_response(job)


def get_jobs(
    db: Session,
    store_id: Optional[uuid.UUID] = None,
    camera_id: Optional[uuid.UUID] = None,
    job_status: Optional[str] = None,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
) -> tuple[list[AIJobResponse], int]:
    """
    List AI jobs with optional filters.
    Returns (items, total_count).
    """
    query = db.query(AIJob)

    if store_id:
        query = query.filter(AIJob.store_id == store_id)
    if camera_id:
        query = query.filter(AIJob.camera_id == camera_id)
    if job_status:
        query = query.filter(AIJob.status == job_status)

    query = query.order_by(AIJob.created_at.desc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    jobs = query.all()
    return [_to_response(j) for j in jobs], total


def request_stop(
    db: Session,
    job_id: uuid.UUID,
) -> AIJobResponse:
    """
    Request to stop a running AI job.
    Only QUEUED or RUNNING jobs can be stopped.
    """
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI job with id '{job_id}' not found.",
        )

    if job.status not in ("QUEUED", "RUNNING"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot stop job with status '{job.status}'. "
                   f"Only QUEUED or RUNNING jobs can be stopped.",
        )

    if job.status == "QUEUED":
        # If still queued (not yet started), just mark as stopped
        job.status = "STOPPED"
        job.error_message = "Job was stopped before processing started."
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(job)
    else:
        # Try to stop the running process
        stopped = worker_stop_job(job_id)
        if not stopped:
            # Process may have already finished; refresh from DB
            db.refresh(job)

    return _to_response(job)


def get_job_results(
    db: Session,
    job_id: uuid.UUID,
) -> AIJobResultsResponse:
    """
    Get detailed results for a completed AI job.
    Reads the Phase 6 report and lists available output files.
    """
    job = db.query(AIJob).filter(AIJob.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI job with id '{job_id}' not found.",
        )

    if job.status != "COMPLETED":
        return AIJobResultsResponse(
            job_id=job.id,
            camera_id=job.camera_id,
            store_id=job.store_id,
            status=job.status,
            summary=job.summary,
        )

    # Resolve output directory
    project_root = _get_project_root()
    output_dir = None
    if job.output_path:
        op = Path(job.output_path)
        output_dir = op if op.is_absolute() else (project_root / op)

    # Read Phase 6 report for detailed results
    reports = None
    markdown_report = None
    available_files = []
    annotated_video = False

    if output_dir and output_dir.exists():
        # Try to read the full Phase 6 report
        report_dir = output_dir / "phase6" / "reports"
        if report_dir.exists():
            json_files = list(report_dir.glob("*.json"))
            if json_files:
                try:
                    with open(json_files[0], "r", encoding="utf-8") as f:
                        reports = json.load(f)
                except Exception:
                    pass

            md_files = list(report_dir.glob("*.md"))
            if md_files:
                try:
                    with open(md_files[0], "r", encoding="utf-8") as f:
                        markdown_report = f.read()
                except Exception:
                    pass

        # Also fallback check phase5 reports if phase6 reports are absent
        if not reports:
            p5_report_dir = output_dir / "phase5" / "reports"
            if p5_report_dir.exists():
                p5_json_files = list(p5_report_dir.glob("*.json"))
                if p5_json_files:
                    try:
                        with open(p5_json_files[0], "r", encoding="utf-8") as f:
                            reports = json.load(f)
                    except Exception:
                        pass
                p5_md_files = list(p5_report_dir.glob("*.md"))
                if not markdown_report and p5_md_files:
                    try:
                        with open(p5_md_files[0], "r", encoding="utf-8") as f:
                            markdown_report = f.read()
                    except Exception:
                        pass

        # List available files
        for phase_dir in sorted(output_dir.iterdir()):
            if phase_dir.is_dir():
                for sub_dir in sorted(phase_dir.iterdir()):
                    if sub_dir.is_dir():
                        for f in sorted(sub_dir.iterdir()):
                            if f.is_file() and not f.name.startswith("."):
                                rel = f.relative_to(output_dir)
                                available_files.append(str(rel))
                                # Check for annotated video
                                if sub_dir.name == "videos" and f.suffix in (".mp4", ".avi", ".mkv"):
                                    annotated_video = True

    # Fallback to extract summary from reports if job.summary in DB is empty
    summary = job.summary
    if (not summary or not isinstance(summary, dict) or not summary.get("unique_shoppers")) and reports:
        from app.services.ai_worker import _extract_summary
        extracted = _extract_summary(reports)
        if extracted:
            summary = extracted

    return AIJobResultsResponse(
        job_id=job.id,
        camera_id=job.camera_id,
        store_id=job.store_id,
        status=job.status,
        summary=summary,
        reports=reports,
        markdown_report=markdown_report,
        available_files=available_files,
        annotated_video_available=annotated_video,
    )


def get_job_report(
    db: Session,
    job_id: uuid.UUID,
) -> AIJobReportResponse:
    """
    Retrieve full structured JSON and Markdown reports for a completed Module 3 AI job.
    """
    results = get_job_results(db, job_id)
    json_report = results.reports or {"summary": results.summary or {}}
    markdown_report = results.markdown_report or ""

    if not markdown_report and results.summary:
        # Fallback generate clean Markdown summary if .md file is not on disk
        lines = [
            "# Module 3 — Consumer Tracking & Movement Analytics Report",
            "",
            "> **Phase 6: Executive Analytics Summary**",
            "",
            "## Summary Metrics",
            "",
            "| Metric | Value |",
            "| :--- | :--- |",
        ]
        for k, v in results.summary.items():
            if isinstance(v, dict):
                lines.append(f"| **{k.replace('_', ' ').title()}** | {v.get('zone_name') or v.get('target_name') or json.dumps(v)} |")
            else:
                lines.append(f"| **{k.replace('_', ' ').title()}** | {v} |")
        markdown_report = "\n".join(lines)

    return AIJobReportResponse(
        job_id=job_id,
        json_report=json_report,
        markdown_report=markdown_report,
    )



def get_job_output_file(
    db: Session,
    job_id: uuid.UUID,
    file_path: str,
) -> Path:
    """
    Resolve and validate a job output file path.
    Returns the absolute file path if valid.

    Raises HTTPException if:
        - Job not found
        - Job not completed
        - File not found
        - Path traversal detected
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
            detail=f"Job is not completed (status: {job.status}).",
        )

    if not job.output_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job has no output path.",
        )

    project_root = _get_project_root()
    output_dir = (project_root / job.output_path).resolve()

    # Resolve requested file path
    requested_file = (output_dir / file_path).resolve()

    # Prevent path traversal
    if not str(requested_file).startswith(str(output_dir)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file path.",
        )

    if not requested_file.exists() or not requested_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}",
        )

    return requested_file
