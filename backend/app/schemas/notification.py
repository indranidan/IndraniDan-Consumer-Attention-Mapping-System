"""
Notification Schemas
=====================
Pydantic models for alert/notification CRUD, filtering, and responses.
"""

import uuid
from datetime import datetime
from typing import Any

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


# ── Response Schemas ──────────────────────────────────────────

class NotificationResponse(BaseModel):
    """Full notification response returned by list/detail endpoints."""

    id: uuid.UUID
    store_id: uuid.UUID | None = None
    type: str
    severity: str
    title: str
    message: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    target_role: str = "all"
    is_read: bool = False
    is_resolved: bool = False
    metadata: dict[str, Any] | None = Field(default=None, alias="metadata_json")
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}


class NotificationCountResponse(BaseModel):
    """Compact unread count response for the navbar badge."""

    unread_count: int = 0


# ── Request / Filter Schemas ─────────────────────────────────

class NotificationListParams(BaseModel):
    """Query parameters for listing notifications."""

    store_id: uuid.UUID | None = None
    severity: str | None = None
    type: str | None = None
    is_read: bool | None = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class NotificationResolveRequest(BaseModel):
    """Body for resolving an alert."""

    resolution_note: str | None = Field(
        default=None,
        max_length=500,
        description="Optional note describing the resolution action",
    )
