"""
Reports & Export API Router
===========================
REST endpoints for Module 12: Reports & Export System:
- GET  /api/reports/templates   Catalog of available report templates
- POST /api/reports/preview     Zero-latency aggregated preview payload
- POST /api/reports/generate    Generate and save PDF/Excel/CSV/JSON dossier
- GET  /api/reports/ledger      List historical reports with metadata
- GET  /api/reports/{id}/download Stream report binary artifact
- DELETE /api/reports/{id}      Remove report artifact and record
"""

import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.dependencies import any_role, admin_or_store_manager
from app.database.database import get_db
from app.models.user import User
from app.schemas.report import (
    ReportGenerateRequest,
    ReportLedgerResponse,
    ReportPreviewRequest,
    ReportPreviewResponse,
    ReportRecordOut,
    ReportTemplateOut,
)
from app.services.report_service import report_service

router = APIRouter(prefix="/api/reports", tags=["Reports & Export System"])


@router.get(
    "/templates",
    response_model=List[ReportTemplateOut],
    summary="List available report definitions and templates",
)
def get_report_templates(
    current_user: User = Depends(any_role),
):
    """Retrieve catalog of available retail intelligence domain templates."""
    return report_service.get_templates()


@router.post(
    "/preview",
    response_model=ReportPreviewResponse,
    summary="Interactive live report preview without file generation",
)
def preview_report(
    req: ReportPreviewRequest,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Compile instant aggregated summary KPIs, charts, and sample table rows
    for zero-latency UI preview before downloading official dossiers.
    """
    try:
        return report_service.preview_report(db, req)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/generate",
    response_model=ReportRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate official PDF, Excel, CSV, or JSON report artifact",
)
def generate_report(
    req: ReportGenerateRequest,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Compile analytics and render an authoritative dossier file (PDF, Excel, CSV, or JSON).
    Saves document to disk and registers the artifact in the report ledger.
    """
    try:
        return report_service.generate_report(db, req, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report generation failed: {str(e)}",
        )


@router.get(
    "/ledger",
    response_model=ReportLedgerResponse,
    summary="List historical generated reports",
)
def get_report_ledger(
    store_id: Optional[uuid.UUID] = Query(None, description="Filter by store"),
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Retrieve chronological history of generated reports with file sizes and download URLs."""
    total, reports = report_service.list_reports(
        db=db,
        store_id=store_id,
        report_type=report_type,
        skip=skip,
        limit=limit,
    )
    return ReportLedgerResponse(total=total, reports=reports)


@router.get(
    "/{report_id}/download",
    summary="Download compiled report artifact",
)
def download_report(
    report_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Stream compiled PDF, Excel, CSV, or JSON file directly with attachment disposition.
    Requires authenticated user with any valid role.
    """
    from app.core.config import get_settings
    settings = get_settings()

    record = report_service.get_report(db, report_id)
    if not record or not record.file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    file_path = Path(record.file_path).resolve()

    # Canonical path confinement: ensure file is inside reports output directory
    _BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
    _ROOT_DIR = _BACKEND_DIR.parent
    reports_root = (_ROOT_DIR / settings.REPORTS_OUTPUT_PATH).resolve()
    try:
        file_path.relative_to(reports_root)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: file is outside the authorized reports directory.",
        )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Report artifact file has been pruned or removed from disk",
        )

    # Determine MIME type
    media_types = {
        "pdf": "application/pdf",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "csv": "text/csv; charset=utf-8",
        "json": "application/json",
    }
    media_type = media_types.get(record.format.lower(), "application/octet-stream")

    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name,
    )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete report artifact and ledger record",
)
def delete_report(
    report_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Remove a previously generated report artifact from disk and delete database record."""
    success = report_service.delete_report(db, report_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return None
