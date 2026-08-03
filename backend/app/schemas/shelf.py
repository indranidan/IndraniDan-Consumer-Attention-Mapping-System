"""
Shelf Schemas
=============
Pydantic models for shelf CRUD operations.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ShelfCreate(BaseModel):
    """Schema for creating a new shelf."""

    store_id: uuid.UUID = Field(..., description="UUID of the parent store")
    zone_id: uuid.UUID = Field(..., description="UUID of the parent zone")
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Shelf A-1"],
        description="Shelf display name",
    )
    shelf_code: str = Field(
        ...,
        min_length=1,
        max_length=50,
        examples=["SH-001"],
        description="Unique shelf identifier code",
    )
    category: str | None = Field(
        default=None,
        max_length=100,
        examples=["Beverages"],
    )
    description: str | None = Field(
        default=None,
        examples=["Top shelf for premium beverages"],
    )


class ShelfUpdate(BaseModel):
    """Schema for updating a shelf. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    shelf_code: str | None = Field(default=None, min_length=1, max_length=50)
    category: str | None = Field(default=None, max_length=100)
    description: str | None = None


class ShelfResponse(BaseModel):
    """Schema for shelf response."""

    id: uuid.UUID
    store_id: uuid.UUID
    zone_id: uuid.UUID
    name: str
    shelf_code: str
    category: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    store_name: str = ""
    zone_name: str = ""
    product_count: int = 0

    class Config:
        from_attributes = True
