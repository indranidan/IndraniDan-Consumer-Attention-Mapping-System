"""
Zone Routes
============
CRUD endpoints for store zones.

Endpoints:
    POST   /api/zones           Create a new zone
    GET    /api/zones           List all zones
    GET    /api/zones/{id}      Get zone by ID
    PUT    /api/zones/{id}      Update a zone
    DELETE /api/zones/{id}      Delete a zone
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse
from app.schemas.auth import MessageResponse
from app.middleware.jwt_auth import get_current_user
from app.core.dependencies import admin_or_store_manager, any_role
from app.services import zone_service
from app.core.cache import cache_manager, invalidate_cache_tags

router = APIRouter(prefix="/api/zones", tags=["Zones"])


@router.post(
    "",
    response_model=ZoneResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new zone",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Store not found"},
        422: {"description": "Validation error"},
    },
)
def create_zone(
    payload: ZoneCreate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Create a new zone within a store. Requires Administrator or Store Manager role."""
    result = zone_service.create_zone(db, payload)
    invalidate_cache_tags("zones", "dashboard")
    return result


@router.get(
    "",
    response_model=list[ZoneResponse],
    summary="List all zones",
)
def list_zones(
    response: Response,
    store_id: uuid.UUID | None = Query(default=None, description="Filter by store ID"),
    search: str | None = Query(default=None, description="Search by name or description"),
    name: str | None = Query(default=None, description="Filter by zone name"),
    page: int | None = Query(default=None, ge=1, description="Page number (1-indexed)"),
    page_size: int | None = Query(default=None, ge=1, le=50, description="Items per page (max 50)"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List all zones with sub-millisecond response caching. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"zones:list:{store_id}:{search}:{name}:{page}:{page_size}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        response.headers["X-Total-Count"] = str(cached.get("total", 0))
        return cached.get("items", [])

    items, total = zone_service.get_zones(
        db, store_id=store_id, search=search, name=name, page=page, page_size=page_size
    )
    response.headers["X-Total-Count"] = str(total)
    serialized = [ZoneResponse.model_validate(item).model_dump(mode="json") for item in items]
    cache_manager.set(cache_key, {"items": serialized, "total": total}, ttl_seconds=60.0, tags=["zones"])
    return items


@router.get(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Get zone details",
    responses={404: {"description": "Zone not found"}},
)
def get_zone(
    zone_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a zone by its ID. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"zone:{zone_id}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached


    zone = zone_service.get_zone_by_id(db, zone_id)
    if zone:
        cache_manager.set(cache_key, ZoneResponse.model_validate(zone).model_dump(mode="json"), ttl_seconds=60.0, tags=["zones"])
    return zone


@router.put(
    "/{zone_id}",
    response_model=ZoneResponse,
    summary="Update a zone",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Zone not found"},
    },
)
def update_zone(
    zone_id: uuid.UUID,
    payload: ZoneUpdate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Update a zone. Requires Administrator or Store Manager role."""
    result = zone_service.update_zone(db, zone_id, payload)
    invalidate_cache_tags("zones", "dashboard")
    return result


@router.delete(
    "/{zone_id}",
    response_model=MessageResponse,
    summary="Delete a zone",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Zone not found"},
    },
)
def delete_zone(
    zone_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Delete a zone and all its shelves and products. Requires Administrator or Store Manager role."""
    zone_service.delete_zone(db, zone_id)
    invalidate_cache_tags("zones", "shelves", "products", "dashboard")
    return MessageResponse(message="Zone deleted successfully.")

