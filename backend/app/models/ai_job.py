"""
AI Job Model
=============
Represents an AI analysis processing job.
Each job processes a camera/video source through the Module 3 pipeline.
"""

from app.models import User
from app.models import Store
from app.models import Camera
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class AIJob(Base):
    """
    AI Jobs table — tracks AI analysis processing jobs.

    Notes:
        - Every job is associated with a camera and store.
        - status tracks the lifecycle: QUEUED → RUNNING → COMPLETED/FAILED/STOPPED.
        - input_type specifies the input source mode: VIDEO_FILE, WEBCAM, FUTURE_CAMERA.
        - summary stores compact analytics results as JSON after completion.
        - output_path points to the job's output directory (relative).
        - Large outputs (videos, charts, detailed reports) are stored on the filesystem.
    """

    __tablename__ = "ai_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    camera_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cameras.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the camera being analyzed",
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="FK to the parent store",
    )
    input_type: Mapped[str] = mapped_column(
        String(20),
        default="VIDEO_FILE",
        nullable=False,
        comment="Input source type: VIDEO_FILE, WEBCAM, FUTURE_CAMERA",
    )
    source: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Video source path or camera feed URL used for analysis",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="QUEUED",
        nullable=False,
        index=True,
        comment="Job status: QUEUED, RUNNING, COMPLETED, FAILED, STOPPED",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when processing started",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when processing completed or failed",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if job failed",
    )
    output_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Relative path to job output directory",
    )
    summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Compact analytics summary JSON after completion",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to the user who created this job",
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
    camera: Mapped["Camera"] = relationship(  # noqa: F821
        "Camera",
        lazy="joined",
    )
    store: Mapped["Store"] = relationship(  # noqa: F821
        "Store",
        lazy="joined",
    )
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[created_by],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<AIJob(id={self.id}, camera_id={self.camera_id}, status='{self.status}')>"
