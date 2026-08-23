"""
AI Job Schemas
===============
Pydantic models for AI job CRUD operations and result responses.
"""

import uuid
from datetime import datetime
from typing import Any

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class AIJobCreate(BaseModel):
    """Schema for creating a new AI analysis job."""

    store_id: uuid.UUID = Field(
        ...,
        description="UUID of the store",
    )
    camera_id: uuid.UUID = Field(
        ...,
        description="UUID of the camera to analyze",
    )
    input_type: str = Field(
        default="VIDEO_FILE",
        description="Input source type: VIDEO_FILE, WEBCAM, FUTURE_CAMERA",
    )
    source_override: str | None = Field(
        default=None,
        max_length=500,
        description="Optional override for the video source path or camera index",
    )
    zone_config: dict[str, Any] | None = Field(
        default=None,
        description="Optional calibrated zone configuration for the video",
    )


class AIJobResponse(BaseModel):
    """Full AI job response with all details."""

    id: uuid.UUID
    camera_id: uuid.UUID
    store_id: uuid.UUID
    input_type: str = "VIDEO_FILE"
    source: str
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    output_path: str | None
    summary: dict[str, Any] | None
    zone_config: dict[str, Any] | None = None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # Denormalized names for display
    camera_name: str = ""
    store_name: str = ""
    creator_name: str = ""

    class Config:
        from_attributes = True


class AIJobStatusResponse(BaseModel):
    """Lightweight status check response."""

    id: uuid.UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class AIJobResultsResponse(BaseModel):
    """Full results response after job completion."""

    job_id: uuid.UUID
    camera_id: uuid.UUID
    store_id: uuid.UUID
    status: str
    summary: dict[str, Any] | None
    reports: dict[str, Any] | None = None
    markdown_report: str | None = None
    available_files: list[str] = []
    annotated_video_available: bool = False


class AIJobReportResponse(BaseModel):
    """Structured report response for an AI job."""

    job_id: uuid.UUID
    json_report: dict[str, Any]
    markdown_report: str

