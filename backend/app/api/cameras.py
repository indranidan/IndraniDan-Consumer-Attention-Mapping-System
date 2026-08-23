"""
Camera Routes
==============
CRUD endpoints for cameras.

Endpoints:
    POST   /api/cameras           Create a new camera
    GET    /api/cameras           List all cameras
    GET    /api/cameras/{id}      Get camera by ID
    PUT    /api/cameras/{id}      Update a camera
    DELETE /api/cameras/{id}      Delete a camera
"""

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse
from app.schemas.auth import MessageResponse
from app.core.dependencies import admin_or_store_manager, any_role
from app.services import camera_service
from app.core.cache import cache_manager, invalidate_cache_tags

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])


@router.post(
    "",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new camera",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Store or zone not found"},
        422: {"description": "Validation error"},
    },
)
def create_camera(
    payload: CameraCreate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Create a new camera. Requires Administrator or Store Manager role."""
    result = camera_service.create_camera(db, payload)
    invalidate_cache_tags("cameras", "dashboard")
    return result


@router.get(
    "",
    response_model=list[CameraResponse],
    summary="List all cameras",
)
def list_cameras(
    response: Response,
    store_id: uuid.UUID | None = Query(default=None, description="Filter by store ID"),
    zone_id: uuid.UUID | None = Query(default=None, description="Filter by zone ID"),
    search: str | None = Query(default=None, description="Search by name or source"),
    status: str | None = Query(default=None, description="Filter by status"),
    page: int | None = Query(default=None, ge=1, description="Page number (1-indexed)"),
    page_size: int | None = Query(default=None, ge=1, le=50, description="Items per page (max 50)"),
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """List all cameras with sub-millisecond response caching. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"cameras:list:{store_id}:{zone_id}:{search}:{status}:{page}:{page_size}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        response.headers["X-Total-Count"] = str(cached.get("total", 0))
        return cached.get("items", [])

    items, total = camera_service.get_cameras(
        db, store_id=store_id, zone_id=zone_id, search=search, status=status,
        page=page, page_size=page_size
    )
    response.headers["X-Total-Count"] = str(total)
    serialized = [CameraResponse.model_validate(item).model_dump(mode="json") for item in items]
    cache_manager.set(cache_key, {"items": serialized, "total": total}, ttl_seconds=60.0, tags=["cameras"])
    return items


@router.get(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Get camera details",
    responses={404: {"description": "Camera not found"}},
)
def get_camera(
    camera_id: uuid.UUID,
    response: Response,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Get a camera by its ID. Available to all authenticated users."""
    response.headers["Cache-Control"] = "public, max-age=30, stale-while-revalidate=60"
    cache_key = f"camera:{camera_id}"
    cached = cache_manager.get(cache_key)
    if cached is not None:
        return cached


    camera = camera_service.get_camera_by_id(db, camera_id)
    if camera:
        cache_manager.set(cache_key, CameraResponse.model_validate(camera).model_dump(mode="json"), ttl_seconds=60.0, tags=["cameras"])
    return camera


@router.put(
    "/{camera_id}",
    response_model=CameraResponse,
    summary="Update a camera",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Camera or zone not found"},
    },
)
def update_camera(
    camera_id: uuid.UUID,
    payload: CameraUpdate,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Update a camera. Requires Administrator or Store Manager role."""
    result = camera_service.update_camera(db, camera_id, payload)
    invalidate_cache_tags("cameras", "dashboard")
    return result


@router.delete(
    "/{camera_id}",
    response_model=MessageResponse,
    summary="Delete a camera",
    responses={
        403: {"description": "Insufficient permissions"},
        404: {"description": "Camera not found"},
    },
)
def delete_camera(
    camera_id: uuid.UUID,
    current_user: User = Depends(admin_or_store_manager),
    db: Session = Depends(get_db),
):
    """Delete a camera. Requires Administrator or Store Manager role."""
    camera_service.delete_camera(db, camera_id)
    invalidate_cache_tags("cameras", "dashboard")
    return MessageResponse(message="Camera deleted successfully.")



@router.post(
    "/{camera_id}/test",
    summary="Test live camera stream connectivity and latency",
)
def test_camera(
    camera_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Probes RTSP/HTTP or device stream connectivity with safety timeout."""
    return camera_service.probe_camera_stream(db, camera_id)


@router.get(
    "/{camera_id}/snapshot",
    summary="Capture single frame snapshot preview from camera",
)
def get_camera_snapshot(
    camera_id: uuid.UUID,
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """Captures and returns base64 image frame from camera."""
    return camera_service.capture_camera_snapshot(db, camera_id)

