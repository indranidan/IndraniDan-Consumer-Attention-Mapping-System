"""
Shelf Service
=============
Business logic for shelf CRUD operations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException, status

from app.models.shelf import Shelf
from app.models.store import Store
from app.models.zone import Zone
from app.schemas.shelf import ShelfCreate, ShelfUpdate, ShelfResponse


def _to_response(shelf: Shelf) -> ShelfResponse:
    """Convert a Shelf ORM object to a ShelfResponse schema."""
    return ShelfResponse(
        id=shelf.id,
        store_id=shelf.store_id,
        zone_id=shelf.zone_id,
        name=shelf.name,
        shelf_code=shelf.shelf_code,
        category=shelf.category,
        description=shelf.description,
        created_at=shelf.created_at,
        updated_at=shelf.updated_at,
        store_name=shelf.store.name if shelf.store else "",
        zone_name=shelf.zone.name if shelf.zone else "",
        product_count=len(shelf.products) if shelf.products else 0,
    )


def create_shelf(db: Session, payload: ShelfCreate) -> ShelfResponse:
    """
    Create a new shelf.

    Validates:
        - Store must exist (404)
        - Zone must exist (404)
        - shelf_code must be unique (409)
    """
    # Validate store exists
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{payload.store_id}' not found.",
        )

    # Validate zone exists
    zone = db.query(Zone).filter(Zone.id == payload.zone_id).first()
    if not zone:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Zone with id '{payload.zone_id}' not found.",
        )

    # Check shelf_code uniqueness
    existing = db.query(Shelf).filter(Shelf.shelf_code == payload.shelf_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A shelf with code '{payload.shelf_code}' already exists.",
        )

    shelf = Shelf(
        id=uuid.uuid4(),
        store_id=payload.store_id,
        zone_id=payload.zone_id,
        name=payload.name,
        shelf_code=payload.shelf_code,
        category=payload.category,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(shelf)
    db.commit()
    db.refresh(shelf)

    return _to_response(shelf)


def get_shelves(
    db: Session,
    store_id: uuid.UUID | None = None,
    zone_id: uuid.UUID | None = None,
    search: str | None = None,
    category: str | None = None,
    shelf_code: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[list[ShelfResponse], int]:
    """List shelves with optional filters. Returns (items, total_count)."""
    query = db.query(Shelf)

    if store_id:
        query = query.filter(Shelf.store_id == store_id)
    if zone_id:
        query = query.filter(Shelf.zone_id == zone_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Shelf.name.ilike(search_filter)
            | Shelf.shelf_code.ilike(search_filter)
            | Shelf.category.ilike(search_filter)
        )

    # ── Individual Filters ────────────────────────────────────
    if category:
        query = query.filter(Shelf.category.ilike(category))
    if shelf_code:
        query = query.filter(Shelf.shelf_code.ilike(shelf_code))

    query = query.order_by(Shelf.created_at.desc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    shelves = query.options(
        joinedload(Shelf.store),
        joinedload(Shelf.zone),
        selectinload(Shelf.products),
    ).all()
    return [_to_response(s) for s in shelves], total


def get_shelf_by_id(db: Session, shelf_id: uuid.UUID) -> ShelfResponse:
    """Get a single shelf by ID. Raises 404 if not found."""
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelf with id '{shelf_id}' not found.",
        )
    return _to_response(shelf)


def update_shelf(
    db: Session,
    shelf_id: uuid.UUID,
    payload: ShelfUpdate,
) -> ShelfResponse:
    """Update an existing shelf."""
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelf with id '{shelf_id}' not found.",
        )

    # Check shelf_code uniqueness if being changed
    if payload.shelf_code is not None and payload.shelf_code != shelf.shelf_code:
        existing = db.query(Shelf).filter(Shelf.shelf_code == payload.shelf_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A shelf with code '{payload.shelf_code}' already exists.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(shelf, field, value)

    shelf.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(shelf)

    return _to_response(shelf)


def delete_shelf(db: Session, shelf_id: uuid.UUID) -> None:
    """Delete a shelf by ID. Cascades to products."""
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelf with id '{shelf_id}' not found.",
        )

    db.delete(shelf)
    db.commit()
