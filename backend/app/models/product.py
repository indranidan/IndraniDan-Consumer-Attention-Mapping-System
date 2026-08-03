"""
Product Model
=============
Represents a product placed on a shelf within a store.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Product(Base):
    """
    Products table — items placed on shelves.

    Notes:
        - Every product belongs to a store, zone, and shelf.
        - sku (Stock Keeping Unit) is unique across the system.
        - price is stored as Numeric for precision.
    """

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the parent store",
    )
    zone_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the parent zone",
    )
    shelf_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shelves.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the parent shelf",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Product display name",
    )
    sku: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique Stock Keeping Unit code",
    )
    brand: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Product brand name",
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Product category",
    )
    price: Mapped[float | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Product price",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional product description",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    store: Mapped["Store"] = relationship(  # noqa: F821
        "Store",
        back_populates="products",
        lazy="joined",
    )
    zone: Mapped["Zone"] = relationship(  # noqa: F821
        "Zone",
        lazy="joined",
    )
    shelf: Mapped["Shelf"] = relationship(  # noqa: F821
        "Shelf",
        back_populates="products",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', sku='{self.sku}')>"
