"""
Module 5 — Product Interaction Analysis Database Models
=========================================================
SQLAlchemy models for persisting Module 5 product interaction analysis
summaries, shelf interactions, product engagement, and interaction events.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

# pyrefly: ignore [missing-import]
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class ProductInteractionAnalysis(Base):
    """
    Product Interaction Analyses table — stores aggregate Module 5 analysis results for an AI job.
    """

    __tablename__ = "product_interaction_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        comment="FK to parent AI job",
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to camera",
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to store",
    )
    total_views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total product view events",
    )
    total_pickups: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total verified product pickup events",
    )
    total_returns: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total verified product return events",
    )
    total_comparisons: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total multi-product comparison patterns observed",
    )
    total_purchases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total purchases from POS (0 if unconfigured)",
    )
    total_unique_viewers: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total unique shopper tracking IDs who viewed products/shelves",
    )
    total_engagement_duration_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Cumulative engagement duration in seconds",
    )
    pickup_detection_status: Mapped[str] = mapped_column(
        String(100),
        default="INSUFFICIENT_VISUAL_EVIDENCE",
        nullable=False,
        comment="Status of pickup visual evidence",
    )
    purchase_data_status: Mapped[str] = mapped_column(
        String(100),
        default="UNAVAILABLE / NOT CONFIGURED (No POS Data)",
        nullable=False,
        comment="Status of purchase transaction integration",
    )
    product_metrics: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array of per-product engagement metrics",
    )
    shelf_metrics: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array of per-shelf interaction metrics",
    )
    comparison_patterns: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array of multi-product comparison sequences",
    )
    summary_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Full summary payload for Module 5",
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

    # Relationships
    job: Mapped["AIJob"] = relationship(  # noqa: F821
        "AIJob",
        lazy="joined",
    )
    camera: Mapped["Camera"] = relationship(  # noqa: F821
        "Camera",
        lazy="joined",
    )
    store: Mapped["Store"] = relationship(  # noqa: F821
        "Store",
        lazy="joined",
    )
    events: Mapped[List["ProductInteractionEventModel"]] = relationship(
        "ProductInteractionEventModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductInteractionAnalysis(id={self.id}, job_id={self.job_id}, "
            f"views={self.total_views}, pickups={self.total_pickups}, comparisons={self.total_comparisons})>"
        )


class ProductInteractionEventModel(Base):
    """
    Product Interaction Events table — granular record of every product interaction event.
    """

    __tablename__ = "product_interaction_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("product_interaction_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent product interaction analysis",
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent AI job",
    )
    event_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Unique event identifier string",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="PRODUCT_VIEWED, PRODUCT_PICKED_UP, PRODUCT_RETURNED, PRODUCT_PURCHASED, PRODUCT_COMPARED",
    )
    track_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
        comment="ByteTrack tracking ID",
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Associated session ID",
    )
    product_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Associated product ID or code",
    )
    product_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Product display name",
    )
    sku: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Stock Keeping Unit code",
    )
    shelf_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Shelf identifier code",
    )
    shelf_name: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Shelf display name",
    )
    camera_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cameras.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to camera",
    )
    store_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("stores.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to store",
    )
    timestamp: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Start timestamp in seconds into video",
    )
    start_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Event start timestamp in seconds",
    )
    end_time: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Event end timestamp in seconds",
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Event duration in seconds",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Detection confidence score (0.0 to 1.0)",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        default="MODULE_4_ATTENTION",
        nullable=False,
        comment="Source of event: MODULE_4_ATTENTION, SPATIAL_INTERACTION, POS_TRANSACTION, BEHAVIORAL_HEURISTIC",
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Extra metadata such as comparison sequences, bounding boxes, or verification notes",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["ProductInteractionAnalysis"] = relationship(
        "ProductInteractionAnalysis",
        back_populates="events",
    )

    def __repr__(self) -> str:
        return (
            f"<ProductInteractionEvent(id={self.id}, type='{self.event_type}', "
            f"track_id={self.track_id}, product='{self.product_name}', duration={self.duration_seconds}s)>"
        )
