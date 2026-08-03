"""
Zone Model
==========
Represents a zone within a retail store.
Zones are logical areas (e.g., Entrance, Aisle 1, Checkout).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Zone(Base):
    """
    Zones table — logical areas within a store.

    Notes:
        - Every zone belongs to exactly one store.
        - A zone can contain multiple shelves and cameras.
    """

    __tablename__ = "zones"

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
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Zone display name",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional zone description",
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
        back_populates="zones",
        lazy="joined",
    )
    shelves: Mapped[list["Shelf"]] = relationship(  # noqa: F821
        "Shelf",
        back_populates="zone",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    cameras: Mapped[list["Camera"]] = relationship(  # noqa: F821
        "Camera",
        back_populates="zone",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Zone(id={self.id}, name='{self.name}', store_id={self.store_id})>"
