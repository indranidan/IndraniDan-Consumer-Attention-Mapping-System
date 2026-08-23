"""
Product Service
===============
Business logic for product CRUD operations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.product import Product
from app.models.store import Store
from app.models.shelf import Shelf
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse


def _to_response(product: Product) -> ProductResponse:
    """Convert a Product ORM object to a ProductResponse schema."""
    return ProductResponse(
        id=product.id,
        store_id=product.store_id,
        zone_id=product.zone_id,
        shelf_id=product.shelf_id,
        name=product.name,
        sku=product.sku,
        brand=product.brand,
        category=product.category,
        price=float(product.price) if product.price is not None else None,
        description=product.description,
        created_at=product.created_at,
        updated_at=product.updated_at,
        store_name=product.store.name if product.store else "",
        zone_name=product.zone.name if product.zone else "",
        shelf_name=product.shelf.name if product.shelf else "",
    )


def create_product(db: Session, payload: ProductCreate) -> ProductResponse:
    """
    Create a new product.

    Validates:
        - Store must exist (404)
        - Shelf must exist (404)
        - SKU must be unique (409)
    """
    store = db.query(Store).filter(Store.id == payload.store_id).first()
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Store with id '{payload.store_id}' not found.",
        )

    shelf = db.query(Shelf).filter(Shelf.id == payload.shelf_id).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shelf with id '{payload.shelf_id}' not found.",
        )

    existing = db.query(Product).filter(Product.sku == payload.sku).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with SKU '{payload.sku}' already exists.",
        )

    product = Product(
        id=uuid.uuid4(),
        store_id=payload.store_id,
        zone_id=payload.zone_id,
        shelf_id=payload.shelf_id,
        name=payload.name,
        sku=payload.sku,
        brand=payload.brand,
        category=payload.category,
        price=payload.price,
        description=payload.description,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return _to_response(product)


def get_products(
    db: Session,
    store_id: uuid.UUID | None = None,
    shelf_id: uuid.UUID | None = None,
    search: str | None = None,
    zone_id: uuid.UUID | None = None,
    brand: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> tuple[list[ProductResponse], int]:
    """List products with optional filters. Returns (items, total_count)."""
    query = db.query(Product)

    if store_id:
        query = query.filter(Product.store_id == store_id)
    if shelf_id:
        query = query.filter(Product.shelf_id == shelf_id)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            Product.name.ilike(search_filter)
            | Product.sku.ilike(search_filter)
            | Product.brand.ilike(search_filter)
            | Product.category.ilike(search_filter)
        )

    # ── Individual Filters ────────────────────────────────────
    if zone_id:
        query = query.filter(Product.zone_id == zone_id)
    if brand:
        query = query.filter(Product.brand.ilike(brand))
    if category:
        query = query.filter(Product.category.ilike(category))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    query = query.order_by(Product.created_at.desc())
    total = query.count()

    if page is not None and page_size is not None:
        query = query.offset((page - 1) * page_size).limit(page_size)

    products = query.options(
        joinedload(Product.store),
        joinedload(Product.zone),
        joinedload(Product.shelf),
    ).all()
    return [_to_response(p) for p in products], total


def get_product_by_id(db: Session, product_id: uuid.UUID) -> ProductResponse:
    """Get a single product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found.",
        )
    return _to_response(product)


def update_product(
    db: Session,
    product_id: uuid.UUID,
    payload: ProductUpdate,
) -> ProductResponse:
    """Update an existing product."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found.",
        )

    if payload.sku is not None and payload.sku != product.sku:
        existing = db.query(Product).filter(Product.sku == payload.sku).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A product with SKU '{payload.sku}' already exists.",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(product, field, value)

    product.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(product)

    return _to_response(product)


def delete_product(db: Session, product_id: uuid.UUID) -> None:
    """Delete a product by ID."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id '{product_id}' not found.",
        )

    db.delete(product)
    db.commit()
