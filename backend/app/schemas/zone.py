"""
Zone Schemas
============
Pydantic models for zone CRUD operations.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ZoneCreate(BaseModel):
    """Schema for creating a new zone."""

    store_id: uuid.UUID = Field(
        ...,
        description="UUID of the parent store",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Entrance Zone"],
        description="Zone display name",
    )
    description: str | None = Field(
        default=None,
        examples=["Main entrance area with display stands"],
    )


class ZoneUpdate(BaseModel):
    """Schema for updating a zone. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ZoneResponse(BaseModel):
    """Schema for zone response."""

    id: uuid.UUID
    store_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
    store_name: str = ""
    shelf_count: int = 0

    class Config:
        from_attributes = True
