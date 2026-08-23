"""
Zone Service
=============
Business logic for zone CRUD operations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException, status

from app.models.zone import Zone
from app.models.store import Store
from app.schemas.zone import ZoneCreate, ZoneUpdate, ZoneResponse


def _to_response(zone: Zone) -> ZoneResponse:
    """Convert a Zone ORM object to a ZoneResponse schema."""
    return ZoneResponse(
        id=zone.id,
        store_id=zone.store_id,
        name=zone.name,
        description=zone.description,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
        store_name=zone.store.name if zone.store else "",
        shelf_count=len(zone.shelves) if zone.shelves else 0,
    )


def _validate_store_exists(db: Session, store_id: uuid.UUID) -> Store:
    """Validate that a store exists. Raises 404 if not."""
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{store_id}' not found.",
        )
    return store


def create_zone(db: Session, payload: ZoneCreate) -> ZoneResponse:
    """
    Create a new zone within a store.

    Validates:
        - Store must exist (404 if not)
    """
    _validate_store_exists(db, payload.store_id)

    zone = Zone(
        id=uuid.uuid4(),
        store_id=payload.store_id,
        name=payload.name,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(zone)
    db.commit()
    db.refresh(zone)

    return _to_response(zone)


def get_zones(
    db: Session,
    store_id: uuid.UUID | None = None,
    search: str | None = None,
    name: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[list[ZoneResponse], int]:
    """
    List zones, optionally filtered by store, search term, and/or name filter.
    Returns (items, total_count) for pagination support.
    """
    query = db.query(Zone)

    if store_id:
        query = query.filter(Zone.store_id == store_id)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Zone.name.ilike(search_filter)
            | Zone.description.ilike(search_filter)
        )

    # ── Individual Filters ────────────────────────────────────
    if name:
        query = query.filter(Zone.name.ilike(f"%{name}%"))

    query = query.order_by(Zone.created_at.desc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    zones = query.options(
        joinedload(Zone.store),
        selectinload(Zone.shelves),
    ).all()
    return [_to_response(z) for z in zones], total


def get_zone_by_id(db: Session, zone_id: uuid.UUID) -> ZoneResponse:
    """Get a single zone by ID. Raises 404 if not found."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with id '{zone_id}' not found.",
        )
    return _to_response(zone)


def update_zone(
    db: Session,
    zone_id: uuid.UUID,
    payload: ZoneUpdate,
) -> ZoneResponse:
    """Update an existing zone. Raises 404 if not found."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with id '{zone_id}' not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    zone.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(zone)

    return _to_response(zone)


def delete_zone(db: Session, zone_id: uuid.UUID) -> None:
    """Delete a zone by ID. Cascades to shelves and products."""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with id '{zone_id}' not found.",
        )

    db.delete(zone)
    db.commit()
