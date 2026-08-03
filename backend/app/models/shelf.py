"""
Shelf Model
===========
Represents a physical shelf within a store zone.
Shelves hold products and are the primary unit for product placement.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Shelf(Base):
    """
    Shelves table — physical shelving units within a zone.

    Notes:
        - Every shelf belongs to one store and one zone.
        - shelf_code is unique across the system.
        - A shelf can contain multiple products.
    """

    __tablename__ = "shelves"

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
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Shelf display name",
    )
    shelf_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique shelf identifier code",
    )
    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Product category for this shelf",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional shelf description",
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
        back_populates="shelves",
        lazy="joined",
    )
    zone: Mapped["Zone"] = relationship(  # noqa: F821
        "Zone",
        back_populates="shelves",
        lazy="joined",
    )
    products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product",
        back_populates="shelf",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Shelf(id={self.id}, name='{self.name}', code='{self.shelf_code}')>"
