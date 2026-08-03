"""
Shelf Routes
=============
CRUD endpoints for store shelves.

Endpoints:
    POST   /api/shelves           Create a new shelf
    GET    /api/shelves           List all shelves
    GET    /api/shelves/{id}      Get shelf by ID
    PUT    /api/shelves/{id}      Update a shelf
    DELETE /api/shelves/{id}      Delete a shelf
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.shelf import ShelfCreate, ShelfUpdate, ShelfResponse
from app.schemas.auth import MessageResponse
from app.core.dependencies import admin_or_store_manager, any_role
from app.services import shelf_service

router = APIRouter(prefix="/api/shelves", tags=["Shelves"])


@router.post(
    "",
    response_model=ShelfResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new shelf",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Store or zone not found"},
        409: {"description": "Shelf code already exists"},
        422: {"description": "Validation error"},
    },
)
def create_shelf(
    payload: ShelfCreate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Create a new shelf. Requires Administrator or Store Manager role."""
    return shelf_service.create_shelf(db, payload)


@router.get(
    "",
    response_model=list[ShelfResponse],
    summary="List all shelves",
)
def list_shelves(
    response: Response,
    store_id: uuid.UUID | None = Query(default=None, description="Filter by store ID"),
    zone_id: uuid.UUID | None = Query(default=None, description="Filter by zone ID"),
    search: str | None = Query(default=None, description="Search by name, code, or category"),
    category: str | None = Query(default=None, description="Filter by shelf category"),
    shelf_code: str | None = Query(default=None, description="Filter by shelf code"),
    page: int | None = Query(default=None, ge=1, description="Page number (1-indexed)"),
    page_size: int | None = Query(default=None, ge=1, le=50, description="Items per page (max 50)"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List all shelves. Available to all authenticated users."""
    items, total = shelf_service.get_shelves(
        db, store_id=store_id, zone_id=zone_id, search=search,
        category=category, shelf_code=shelf_code,
        page=page, page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/{shelf_id}",
    response_model=ShelfResponse,
    summary="Get shelf details",
    responses={404: {"description": "Shelf not found"}},
)
def get_shelf(
    shelf_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a shelf by its ID. Available to all authenticated users."""
    return shelf_service.get_shelf_by_id(db, shelf_id)


@router.put(
    "/{shelf_id}",
    response_model=ShelfResponse,
    summary="Update a shelf",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Shelf not found"},
        409: {"description": "Shelf code already exists"},
    },
)
def update_shelf(
    shelf_id: uuid.UUID,
    payload: ShelfUpdate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Update a shelf. Requires Administrator or Store Manager role."""
    return shelf_service.update_shelf(db, shelf_id, payload)


@router.delete(
    "/{shelf_id}",
    response_model=MessageResponse,
    summary="Delete a shelf",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Shelf not found"},
    },
)
def delete_shelf(
    shelf_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Delete a shelf and all its products. Requires Administrator or Store Manager role."""
    shelf_service.delete_shelf(db, shelf_id)
    return MessageResponse(message="Shelf deleted successfully.")
