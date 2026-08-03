"""
Store Model
===========
Represents a retail store in the system.
Each store can contain zones, shelves, products, and cameras.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Store(Base):
    """
    Stores table — the top-level entity for retail locations.

    Notes:
        - store_code is unique and indexed for fast lookups.
        - status can be 'active' or 'inactive'.
        - created_by links to the user who created the store.
    """

    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Store display name",
    )
    store_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique store identifier code",
    )
    address: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Street address",
    )
    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="City name",
    )
    state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="State or province",
    )
    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Country name",
    )
    postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Postal or ZIP code",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional store description",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="Store status: active or inactive",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to the user who created this store",
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
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
        lazy="joined",
    )
    zones: Mapped[list["Zone"]] = relationship(  # noqa: F821
        "Zone",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    shelves: Mapped[list["Shelf"]] = relationship(  # noqa: F821
        "Shelf",
        back_populates="store",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product",
        back_populates="store",
        lazy="noload",
        cascade="all, delete-orphan",
    )
    cameras: Mapped[list["Camera"]] = relationship(  # noqa: F821
        "Camera",
        back_populates="store",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Store(id={self.id}, name='{self.name}', code='{self.store_code}')>"
