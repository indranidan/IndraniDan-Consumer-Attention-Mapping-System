"""
Camera Service
==============
Business logic for camera CRUD operations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.camera import Camera
from app.models.store import Store
from app.models.zone import Zone
from app.schemas.camera import CameraCreate, CameraUpdate, CameraResponse


def _to_response(camera: Camera) -> CameraResponse:
    """Convert a Camera ORM object to a CameraResponse schema."""
    return CameraResponse(
        id=camera.id,
        store_id=camera.store_id,
        zone_id=camera.zone_id,
        name=camera.name,
        camera_source=camera.camera_source,
        location_description=camera.location_description,
        status=camera.status,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
        store_name=camera.store.name if camera.store else "",
        zone_name=camera.zone.name if camera.zone else None,
    )


def create_camera(db: Session, payload: CameraCreate) -> CameraResponse:
    """
    Create a new camera.

    Validates:
        - Store must exist (404)
        - Zone must exist if provided (404)
    """
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{payload.store_id}' not found.",
        )

    if payload.zone_id:
        zone = db.query(Zone).filter(Zone.id == payload.zone_id).first()
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with id '{payload.zone_id}' not found.",
            )

    camera = Camera(
        id=uuid.uuid4(),
        store_id=payload.store_id,
        zone_id=payload.zone_id,
        name=payload.name,
        camera_source=payload.camera_source,
        location_description=payload.location_description,
        status=payload.status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(camera)
    db.commit()
    db.refresh(camera)

    return _to_response(camera)


def get_cameras(
    db: Session,
    store_id: uuid.UUID | None = None,
    zone_id: uuid.UUID | None = None,
    search: str | None = None,
    status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[list[CameraResponse], int]:
    """List cameras with optional filters. Returns (items, total_count)."""
    query = db.query(Camera)

    if store_id:
        query = query.filter(Camera.store_id == store_id)
    if zone_id:
        query = query.filter(Camera.zone_id == zone_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Camera.name.ilike(search_filter)
            | Camera.camera_source.ilike(search_filter)
            | Camera.location_description.ilike(search_filter)
        )

    # ── Individual Filters ────────────────────────────────────
    if status:
        query = query.filter(Camera.status == status)

    query = query.order_by(Camera.created_at.desc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    cameras = query.all()
    return [_to_response(c) for c in cameras], total


def get_camera_by_id(db: Session, camera_id: uuid.UUID) -> CameraResponse:
    """Get a single camera by ID."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id '{camera_id}' not found.",
        )
    return _to_response(camera)


def update_camera(
    db: Session,
    camera_id: uuid.UUID,
    payload: CameraUpdate,
) -> CameraResponse:
    """Update an existing camera."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id '{camera_id}' not found.",
        )

    # Validate zone if being changed
    if payload.zone_id is not None:
        zone = db.query(Zone).filter(Zone.id == payload.zone_id).first()
        if not zone:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with id '{payload.zone_id}' not found.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(camera, field, value)

    camera.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(camera)

    return _to_response(camera)


def delete_camera(db: Session, camera_id: uuid.UUID) -> None:
    """Delete a camera by ID."""
    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id '{camera_id}' not found.",
        )

    db.delete(camera)
    db.commit()
