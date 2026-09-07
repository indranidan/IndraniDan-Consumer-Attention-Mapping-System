"""
Report Record Model
===================
Represents generated and archived retail intelligence reports (PDF, Excel, CSV, JSON)
with metadata, audit parameters, KPI summaries, and disk artifact locations.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.database.database import Base


class ReportRecord(Base):
    """
    Reports table — stores generated report dossiers and their execution metadata.

    Notes:
        - report_type: consumer_attention | product_engagement | shelf_performance |
                       conversion_analysis | marketing_effectiveness
        - format: pdf | excel | csv | json
        - status: ready | generating | failed
    """

    __tablename__ = "reports"
    __table_args__ = (
        Index("ix_reports_store_id_report_type", "store_id", "report_type"),
        Index("ix_reports_created_at_desc", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Human-readable report title",
    )
    report_type: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        comment="Domain: consumer_attention, product_engagement, shelf_performance, conversion_analysis, marketing_effectiveness",
    )
    format: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pdf",
        comment="Export format: pdf, excel, csv, json",
    )
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stores.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Target store identifier",
    )
    zone_id: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
        comment="Optional zone filter identifier",
    )
    date_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Start timestamp of analyzed window",
    )
    date_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="End timestamp of analyzed window",
    )
    file_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Relative path on disk for downloading artifact",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="File size in bytes",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="ready",
        nullable=False,
        comment="Generation status: ready, generating, failed",
    )
    parameters: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Input criteria used to compile the report",
    )
    summary_kpis: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Key executive metrics snapshot for rapid card display",
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered report generation",
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

    def __repr__(self) -> str:
        return f"<ReportRecord(id={self.id}, title='{self.title}', type='{self.report_type}', format='{self.format}')>"
