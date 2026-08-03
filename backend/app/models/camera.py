"""
Camera Model
=============
Represents a camera installed in a store, optionally assigned to a zone.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Camera(Base):
    """
    Cameras table — surveillance/tracking cameras within a store.

    Notes:
        - Every camera belongs to a store.
        - zone_id is optional — a camera may or may not be assigned to a zone.
        - camera_source is the feed URL or device identifier.
        - status: active, inactive, or maintenance.
    """

    __tablename__ = "cameras"

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
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="FK to the optional parent zone",
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Camera display name",
    )
    camera_source: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Camera feed URL or device identifier",
    )
    location_description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Description of camera placement",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
        comment="Camera status: active, inactive, or maintenance",
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
        back_populates="cameras",
        lazy="joined",
    )
    zone: Mapped["Zone | None"] = relationship(  # noqa: F821
        "Zone",
        back_populates="cameras",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Camera(id={self.id}, name='{self.name}', store_id={self.store_id})>"
