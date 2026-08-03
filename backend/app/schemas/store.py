"""
Store Schemas
=============
Pydantic models for store CRUD operations.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class StoreCreate(BaseModel):
    """Schema for creating a new store."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Downtown Flagship Store"],
        description="Store display name",
    )
    store_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        examples=["STORE-001"],
        description="Unique store identifier code",
    )
    address: str | None = Field(
        default=None,
        max_length=500,
        examples=["123 Main St"],
    )
    city: str | None = Field(
        default=None,
        max_length=100,
        examples=["New York"],
    )
    state: str | None = Field(
        default=None,
        max_length=100,
        examples=["NY"],
    )
    country: str | None = Field(
        default=None,
        max_length=100,
        examples=["USA"],
    )
    postal_code: str | None = Field(
        default=None,
        max_length=20,
        examples=["10001"],
    )
    description: str | None = Field(
        default=None,
        examples=["Our flagship location in downtown Manhattan"],
    )
    status: str = Field(
        default="active",
        examples=["active"],
        description="Store status: active or inactive",
    )


class StoreUpdate(BaseModel):
    """Schema for updating a store. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    store_code: str | None = Field(default=None, min_length=1, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=20)
    description: str | None = None
    status: str | None = Field(default=None)


class StoreResponse(BaseModel):
    """Schema for store response with all details."""

    id: uuid.UUID
    name: str
    store_code: str
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    postal_code: str | None
    description: str | None
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    zone_count: int = 0
    camera_count: int = 0

    class Config:
        from_attributes = True
