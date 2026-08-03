"""
Camera Schemas
==============
Pydantic models for camera CRUD operations.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CameraCreate(BaseModel):
    """Schema for creating a new camera."""

    store_id: uuid.UUID = Field(..., description="UUID of the parent store")
    zone_id: uuid.UUID | None = Field(
        default=None,
        description="Optional UUID of the zone this camera covers",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Entrance Camera 1"],
        description="Camera display name",
    )
    camera_source: str = Field(
        ...,
        min_length=1,
        max_length=500,
        examples=["rtsp://192.168.1.100:554/stream1"],
        description="Camera feed URL or device identifier",
    )
    location_description: str | None = Field(
        default=None,
        examples=["Mounted above main entrance, facing inward"],
    )
    status: str = Field(
        default="active",
        examples=["active"],
        description="Camera status: active, inactive, or maintenance",
    )


class CameraUpdate(BaseModel):
    """Schema for updating a camera. All fields optional."""

    zone_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    camera_source: str | None = Field(default=None, min_length=1, max_length=500)
    location_description: str | None = None
    status: str | None = None


class CameraResponse(BaseModel):
    """Schema for camera response."""

    id: uuid.UUID
    store_id: uuid.UUID
    zone_id: uuid.UUID | None
    name: str
    camera_source: str
    location_description: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    store_name: str = ""
    zone_name: str | None = None

    class Config:
        from_attributes = True
