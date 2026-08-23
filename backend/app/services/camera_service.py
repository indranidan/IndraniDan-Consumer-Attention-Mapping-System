"""
Camera Service
==============
Business logic for camera CRUD operations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
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

    cameras = query.options(
        joinedload(Camera.store),
        joinedload(Camera.zone),
    ).all()
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


def probe_camera_stream(db: Session, camera_id: uuid.UUID) -> dict:
    """Test accessibility of camera stream URL or index with timeout."""
    import base64
    import time
    import cv2

    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id '{camera_id}' not found.",
        )
    source = camera.camera_source.strip()
    cap_source = int(source) if source.isdigit() else source

    start = time.time()
    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        latency_ms = int((time.time() - start) * 1000)
        return {
            "camera_id": str(camera.id),
            "status": "OFFLINE",
            "message": "Could not connect to camera stream source.",
            "latency_ms": latency_ms,
            "resolution": None,
            "fps": None,
        }

    ret, frame = cap.read()
    latency_ms = int((time.time() - start) * 1000)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()

    if not ret or frame is None:
        return {
            "camera_id": str(camera.id),
            "status": "UNREACHABLE",
            "message": "Connected but unable to decode stream frames.",
            "latency_ms": latency_ms,
            "resolution": None,
            "fps": None,
        }

    return {
        "camera_id": str(camera.id),
        "status": "ONLINE",
        "message": "Camera stream is online and active.",
        "latency_ms": latency_ms,
        "resolution": f"{width}x{height}",
        "fps": round(fps, 1),
    }


def capture_camera_snapshot(db: Session, camera_id: uuid.UUID) -> dict:
    """Capture a single JPEG snapshot from camera stream and return base64 data."""
    import base64
    import cv2

    camera = db.query(Camera).filter(Camera.id == camera_id).first()
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera with id '{camera_id}' not found.",
        )
    source = camera.camera_source.strip()
    cap_source = int(source) if source.isdigit() else source

    cap = cv2.VideoCapture(cap_source)
    if not cap.isOpened():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to open camera stream for snapshot.",
        )
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to read frame from camera stream.",
        )

    _, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    jpg_as_text = base64.b64encode(buffer).decode("utf-8")

    return {
        "camera_id": str(camera.id),
        "camera_name": camera.name,
        "image_data": f"data:image/jpeg;base64,{jpg_as_text}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

