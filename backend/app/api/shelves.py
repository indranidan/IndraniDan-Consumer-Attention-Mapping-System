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
from app.core.cache import cache_manager, invalidate_cache_tags

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
    result = shelf_service.create_shelf(db, payload)
    invalidate_cache_tags("shelves", "dashboard")
    return result


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
    """List all shelves with sub-millisecond response caching. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"shelves:list:{store_id}:{zone_id}:{search}:{category}:{shelf_code}:{page}:{page_size}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        response.headers["X-Total-Count"] = str(cached.get("total", 0))
        return cached.get("items", [])

    items, total = shelf_service.get_shelves(
        db, store_id=store_id, zone_id=zone_id, search=search,
        category=category, shelf_code=shelf_code,
        page=page, page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    serialized = [ShelfResponse.model_validate(item).model_dump(mode="json") for item in items]
    cache_manager.set(cache_key, {"items": serialized, "total": total}, ttl_seconds=60.0, tags=["shelves"])
    return items


@router.get(
    "/{shelf_id}",
    response_model=ShelfResponse,
    summary="Get shelf details",
    responses={404: {"description": "Shelf not found"}},
)
def get_shelf(
    shelf_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a shelf by its ID. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"shelf:{shelf_id}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached


    shelf = shelf_service.get_shelf_by_id(db, shelf_id)
    if shelf:
        cache_manager.set(cache_key, ShelfResponse.model_validate(shelf).model_dump(mode="json"), ttl_seconds=60.0, tags=["shelves"])
    return shelf


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
    result = shelf_service.update_shelf(db, shelf_id, payload)
    invalidate_cache_tags("shelves", "dashboard")
    return result


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
    invalidate_cache_tags("shelves", "products", "dashboard")
    return MessageResponse(message="Shelf deleted successfully.")

