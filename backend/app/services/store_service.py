"""
Store Service
=============
Business logic for store CRUD operations.
Handles validation, uniqueness checks, and database operations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.store import Store
from app.schemas.store import StoreCreate, StoreUpdate, StoreResponse


def _to_response(store: Store) -> StoreResponse:
    """Convert a Store ORM object to a StoreResponse schema."""
    return StoreResponse(
        id=store.id,
        name=store.name,
        store_code=store.store_code,
        address=store.address,
        city=store.city,
        state=store.state,
        country=store.country,
        postal_code=store.postal_code,
        description=store.description,
        status=store.status,
        created_by=store.created_by,
        created_at=store.created_at,
        updated_at=store.updated_at,
        zone_count=len(store.zones) if store.zones else 0,
        camera_count=len(store.cameras) if store.cameras else 0,
    )


def create_store(
    db: Session,
    payload: StoreCreate,
    user_id: uuid.UUID,
) -> StoreResponse:
    """
    Create a new store.

    Validates:
        - store_code uniqueness (409 if duplicate)
    """
    existing = db.query(Store).filter(Store.store_code == payload.store_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A store with code '{payload.store_code}' already exists.",
        )

    store = Store(
        id=uuid.uuid4(),
        name=payload.name,
        store_code=payload.store_code,
        address=payload.address,
        city=payload.city,
        state=payload.state,
        country=payload.country,
        postal_code=payload.postal_code,
        description=payload.description,
        status=payload.status,
        created_by=user_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(store)
    db.commit()
    db.refresh(store)

    return _to_response(store)


def get_stores(
    db: Session,
    search: str | None = None,
    name: str | None = None,
    store_code: str | None = None,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
    status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[list[StoreResponse], int]:
    """
    List all stores, optionally filtered by search term and/or individual filters.
    Returns (items, total_count) for pagination support.
    """
    query = db.query(Store)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Store.name.ilike(search_filter)
            | Store.store_code.ilike(search_filter)
            | Store.city.ilike(search_filter)
            | Store.country.ilike(search_filter)
        )

    # ── Individual Filters ────────────────────────────────────
    if name:
        query = query.filter(Store.name.ilike(f"%{name}%"))
    if store_code:
        query = query.filter(Store.store_code.ilike(store_code))
    if city:
        query = query.filter(Store.city.ilike(city))
    if state:
        query = query.filter(Store.state.ilike(state))
    if country:
        query = query.filter(Store.country.ilike(country))
    if status:
        query = query.filter(Store.status == status)

    query = query.order_by(Store.created_at.desc())
    total = query.count()

    # ── Pagination ────────────────────────────────────────────
    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    stores = query.all()
    return [_to_response(s) for s in stores], total


def get_store_by_id(db: Session, store_id: uuid.UUID) -> StoreResponse:
    """
    Get a single store by ID. Raises 404 if not found.
    """
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{store_id}' not found.",
        )
    return _to_response(store)


def update_store(
    db: Session,
    store_id: uuid.UUID,
    payload: StoreUpdate,
) -> StoreResponse:
    """
    Update an existing store. Raises 404 if not found, 409 if store_code conflict.
    """
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{store_id}' not found.",
        )

    # Check store_code uniqueness if being changed
    if payload.store_code is not None and payload.store_code != store.store_code:
        existing = db.query(Store).filter(Store.store_code == payload.store_code).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A store with code '{payload.store_code}' already exists.",
            )

    # Apply updates for fields that were provided
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(store, field, value)

    store.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(store)

    return _to_response(store)


def delete_store(db: Session, store_id: uuid.UUID) -> None:
    """
    Delete a store by ID. Raises 404 if not found.
    Cascades to zones, shelves, products, and cameras.
    """
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{store_id}' not found.",
        )

    db.delete(store)
    db.commit()
