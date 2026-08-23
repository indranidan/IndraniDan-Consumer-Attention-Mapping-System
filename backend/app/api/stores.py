"""
Store Routes
=============
CRUD endpoints for retail stores.

Endpoints:
    POST   /api/stores           Create a new store
    GET    /api/stores           List all stores
    GET    /api/stores/{id}      Get store by ID
    PUT    /api/stores/{id}      Update a store
    DELETE /api/stores/{id}      Delete a store
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse
from app.schemas.auth import MessageResponse
from app.middleware.jwt_auth import get_current_user
from app.core.dependencies import admin_or_store_manager, admin_only, any_role
from app.services import store_service
from app.core.cache import cache_manager, invalidate_cache_tags

router = APIRouter(prefix="/api/stores", tags=["Stores"])


# ── Create Store ──────────────────────────────────────────────
@router.post(
    "",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new store",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        409: {"description": "Store code already exists"},
        422: {"description": "Validation error"},
    },
)
def create_store(
    payload: StoreCreate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Create a new retail store. Requires Administrator or Store Manager role."""
    result = store_service.create_store(db, payload, current_user.id)
    invalidate_cache_tags("stores", "dashboard")
    return result


# ── List Stores ───────────────────────────────────────────────
@router.get(
    "",
    response_model=list[StoreResponse],
    summary="List all stores",
    responses={
        401: {"description": "Not authenticated"},
    },
)
def list_stores(
    response: Response,
    search: str | None = Query(default=None, description="Search by name, code, city, or country"),
    name: str | None = Query(default=None, description="Filter by store name"),
    store_code: str | None = Query(default=None, description="Filter by store code"),
    city: str | None = Query(default=None, description="Filter by city"),
    state: str | None = Query(default=None, description="Filter by state"),
    country: str | None = Query(default=None, description="Filter by country"),
    status: str | None = Query(default=None, description="Filter by status"),
    page: int | None = Query(default=None, ge=1, description="Page number (1-indexed)"),
    page_size: int | None = Query(default=None, ge=1, le=50, description="Items per page (max 50)"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List all stores with sub-millisecond response caching. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"stores:list:{search}:{name}:{store_code}:{city}:{state}:{country}:{status}:{page}:{page_size}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        response.headers["X-Total-Count"] = str(cached.get("total", 0))
        return cached.get("items", [])

    items, total = store_service.get_stores(
        db, search=search, name=name, store_code=store_code,
        city=city, state=state, country=country, status=status,
        page=page, page_size=page_size,
    )
    response.headers["X-Total-Count"] = str(total)
    
    # Store schema representations in cache
    serialized = [StoreResponse.model_validate(item).model_dump(mode="json") for item in items]
    cache_manager.set(cache_key, {"items": serialized, "total": total}, ttl_seconds=60.0, tags=["stores"])
    return items


# ── Get Store by ID ───────────────────────────────────────────
@router.get(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Get store details",
    responses={
        401: {"description": "Not authenticated"},
        404: {"description": "Store not found"},
    },
)
def get_store(
    store_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a store by its ID. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"store:{store_id}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached

    store = store_service.get_store_by_id(db, store_id)
    if store:
        cache_manager.set(cache_key, StoreResponse.model_validate(store).model_dump(mode="json"), ttl_seconds=60.0, tags=["stores"])
    return store



# ── Update Store ──────────────────────────────────────────────
@router.put(
    "/{store_id}",
    response_model=StoreResponse,
    summary="Update a store",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Store not found"},
        409: {"description": "Store code already exists"},
    },
)
def update_store(
    store_id: uuid.UUID,
    payload: StoreUpdate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Update a store. Requires Administrator or Store Manager role."""
    result = store_service.update_store(db, store_id, payload)
    invalidate_cache_tags("stores", "dashboard")
    return result


# ── Delete Store ──────────────────────────────────────────────
@router.delete(
    "/{store_id}",
    response_model=MessageResponse,
    summary="Delete a store",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Store not found"},
    },
)
def delete_store(
    store_id: uuid.UUID,
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    """
    Delete a store and all its zones, shelves, products, and cameras.
    Requires Administrator role.
    """
    store_service.delete_store(db, store_id)
    invalidate_cache_tags("stores", "zones", "shelves", "products", "cameras", "dashboard")
    return MessageResponse(message="Store deleted successfully.")

