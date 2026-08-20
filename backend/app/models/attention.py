"""
Module 4 — Attention Analysis Database Models
===============================================
SQLAlchemy models for persisting Module 4 attention analysis summaries and events.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class AttentionAnalysis(Base):
    """
    Attention Analyses table — stores aggregate Module 4 analysis results for an AI job.
    """

    __tablename__ = "attention_analyses"

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
    total_events: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Total completed attention events",
    )
    total_attention_duration_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Cumulative attention duration in seconds",
    )
    average_attention_duration_sec: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Average duration per attention event",
    )
    shelf_engagement_score_avg: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Average analytical shelf engagement score (0-100)",
    )
    shelf_metrics: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array of per-shelf engagement metrics",
    )
    product_metrics: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON array of per-product attention metrics (or unconfigured note)",
    )
    quality_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="JSON breakdown of face detection rates and pose confidence",
    )
    summary_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Full summary payload",
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
    events: Mapped[List["AttentionEventModel"]] = relationship(
        "AttentionEventModel",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<AttentionAnalysis(id={self.id}, job_id={self.job_id}, total_events={self.total_events})>"


class AttentionEventModel(Base):
    """
    Attention Events table — granular record of every sustained attention event.
    """

    __tablename__ = "attention_events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attention_analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent attention analysis",
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to parent AI job",
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
    target_type: Mapped[str] = mapped_column(
        String(50),
        default="shelf",
        nullable=False,
        comment="Target type: shelf, product, zone, unknown",
    )
    target_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target identifier code/ID",
    )
    target_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Target display name",
    )
    zone_id: Mapped[str] = mapped_column(
        String(100),
        default="unknown",
        nullable=False,
        comment="Zone where shopper was located",
    )
    start_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Attention event start timestamp (seconds into video)",
    )
    end_time: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Attention event end timestamp (seconds into video)",
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Duration of sustained attention in seconds",
    )
    attention_direction: Mapped[str] = mapped_column(
        String(50),
        default="UNKNOWN",
        nullable=False,
        comment="Discrete estimated direction: LEFT, RIGHT, CENTER, UP, DOWN",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        comment="Mean pose/landmark confidence during event",
    )
    visit_number: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        comment="Visit count for repeated attention tracking",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    analysis: Mapped["AttentionAnalysis"] = relationship(
        "AttentionAnalysis",
        back_populates="events",
    )

    def __repr__(self) -> str:
        return (
            f"<AttentionEvent(id={self.id}, track_id={self.track_id}, "
            f"target='{self.target_name}', duration={self.duration_seconds}s)>"
        )
