"""
Product Schemas
===============
Pydantic models for product CRUD operations.
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    """Schema for creating a new product."""

    store_id: uuid.UUID = Field(..., description="UUID of the parent store")
    zone_id: uuid.UUID = Field(..., description="UUID of the parent zone")
    shelf_id: uuid.UUID = Field(..., description="UUID of the parent shelf")
    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        examples=["Coca-Cola 500ml"],
        description="Product display name",
    )
    sku: str = Field(
        ...,
        min_length=1,
        max_length=100,
        examples=["SKU-CC-500"],
        description="Unique Stock Keeping Unit code",
    )
    brand: str | None = Field(
        default=None,
        max_length=150,
        examples=["Coca-Cola"],
    )
    category: str | None = Field(
        default=None,
        max_length=100,
        examples=["Beverages"],
    )
    price: float | None = Field(
        default=None,
        ge=0,
        examples=[2.99],
        description="Product price",
    )
    description: str | None = Field(
        default=None,
        examples=["500ml bottle of Coca-Cola Classic"],
    )


class ProductUpdate(BaseModel):
    """Schema for updating a product. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    brand: str | None = Field(default=None, max_length=150)
    category: str | None = Field(default=None, max_length=100)
    price: float | None = Field(default=None, ge=0)
    description: str | None = None


class ProductResponse(BaseModel):
    """Schema for product response."""

    id: uuid.UUID
    store_id: uuid.UUID
    zone_id: uuid.UUID
    shelf_id: uuid.UUID
    name: str
    sku: str
    brand: str | None
    category: str | None
    price: float | None
    description: str | None
    created_at: datetime
    updated_at: datetime
    store_name: str = ""
    zone_name: str = ""
    shelf_name: str = ""

    class Config:
        from_attributes = True
