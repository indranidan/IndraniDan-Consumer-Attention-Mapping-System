"""
Product Routes
===============
CRUD endpoints for products.

Endpoints:
    POST   /api/products           Create a new product
    GET    /api/products           List all products
    GET    /api/products/{id}      Get product by ID
    PUT    /api/products/{id}      Update a product
    DELETE /api/products/{id}      Delete a product
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.auth import MessageResponse
from app.core.dependencies import admin_or_store_manager, any_role
from app.services import product_service

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Store or shelf not found"},
        409: {"description": "SKU already exists"},
        422: {"description": "Validation error"},
    },
)
def create_product(
    payload: ProductCreate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Create a new product. Requires Administrator or Store Manager role."""
    return product_service.create_product(db, payload)


@router.get(
    "",
    response_model=list[ProductResponse],
    summary="List all products",
)
def list_products(
    response: Response,
    store_id: uuid.UUID | None = Query(default=None, description="Filter by store ID"),
    shelf_id: uuid.UUID | None = Query(default=None, description="Filter by shelf ID"),
    search: str | None = Query(default=None, description="Search by name, SKU, brand, or category"),
    zone_id: uuid.UUID | None = Query(default=None, description="Filter by zone ID"),
    brand: str | None = Query(default=None, description="Filter by brand"),
    category: str | None = Query(default=None, description="Filter by category"),
    min_price: float | None = Query(default=None, ge=0, description="Minimum price"),
    max_price: float | None = Query(default=None, ge=0, description="Maximum price"),
    page: int | None = Query(default=None, ge=1, description="Page number (1-indexed)"),
    page_size: int | None = Query(default=None, ge=1, le=50, description="Items per page (max 50)"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List all products. Available to all authenticated users."""
    items, total = product_service.get_products(
        db, store_id=store_id, shelf_id=shelf_id, search=search,
        zone_id=zone_id, brand=brand, category=category,
        min_price=min_price, max_price=max_price,
        page=page, page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details",
    responses={404: {"description": "Product not found"}},
)
def get_product(
    product_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a product by its ID. Available to all authenticated users."""
    return product_service.get_product_by_id(db, product_id)


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Product not found"},
        409: {"description": "SKU already exists"},
    },
)
def update_product(
    product_id: uuid.UUID,
    payload: ProductUpdate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Update a product. Requires Administrator or Store Manager role."""
    return product_service.update_product(db, product_id, payload)


@router.delete(
    "/{product_id}",
    response_model=MessageResponse,
    summary="Delete a product",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Product not found"},
    },
)
def delete_product(
    product_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Delete a product. Requires Administrator or Store Manager role."""
    product_service.delete_product(db, product_id)
    return MessageResponse(message="Product deleted successfully.")
