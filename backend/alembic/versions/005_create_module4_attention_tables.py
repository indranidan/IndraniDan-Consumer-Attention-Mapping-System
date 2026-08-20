"""Create Module 4 attention analysis tables (attention_analyses, attention_events)

Revision ID: 005
Revises: 004
Create Date: 2026-08-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create attention_analyses table ────────────────────────
    op.create_table(
        "attention_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="FK to parent AI job"),
        sa.Column("camera_id", sa.Uuid(), nullable=False, comment="FK to camera"),
        sa.Column("store_id", sa.Uuid(), nullable=False, comment="FK to store"),
        sa.Column("total_events", sa.Integer(), nullable=False, server_default="0", comment="Total completed attention events"),
        sa.Column("total_attention_duration_sec", sa.Float(), nullable=False, server_default="0.0", comment="Cumulative attention duration in seconds"),
        sa.Column("average_attention_duration_sec", sa.Float(), nullable=False, server_default="0.0", comment="Average duration per attention event"),
        sa.Column("shelf_engagement_score_avg", sa.Float(), nullable=False, server_default="0.0", comment="Average analytical shelf engagement score (0-100)"),
        sa.Column("shelf_metrics", sa.JSON(), nullable=True, comment="JSON array of per-shelf engagement metrics"),
        sa.Column("product_metrics", sa.JSON(), nullable=True, comment="JSON array of per-product attention metrics"),
        sa.Column("quality_metrics", sa.JSON(), nullable=True, comment="JSON breakdown of face detection rates and pose confidence"),
        sa.Column("summary_data", sa.JSON(), nullable=True, comment="Full summary payload"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
        sa.ForeignKeyConstraint(["job_id"], ["ai_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_attention_analyses_job_id", "attention_analyses", ["job_id"])
    op.create_index("ix_attention_analyses_camera_id", "attention_analyses", ["camera_id"])
    op.create_index("ix_attention_analyses_store_id", "attention_analyses", ["store_id"])

    # ── Create attention_events table ──────────────────────────
    op.create_table(
        "attention_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False, comment="FK to parent attention analysis"),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="FK to parent AI job"),
        sa.Column("track_id", sa.Integer(), nullable=False, comment="ByteTrack tracking ID"),
        sa.Column("session_id", sa.String(100), nullable=True, comment="Associated session ID"),
        sa.Column("target_type", sa.String(50), nullable=False, server_default="shelf", comment="Target type: shelf, product, zone, unknown"),
        sa.Column("target_id", sa.String(100), nullable=False, comment="Target identifier code/ID"),
        sa.Column("target_name", sa.String(200), nullable=False, comment="Target display name"),
        sa.Column("zone_id", sa.String(100), nullable=False, server_default="unknown", comment="Zone where shopper was located"),
        sa.Column("start_time", sa.Float(), nullable=False, comment="Attention event start timestamp"),
        sa.Column("end_time", sa.Float(), nullable=True, comment="Attention event end timestamp"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0.0", comment="Duration of sustained attention in seconds"),
        sa.Column("attention_direction", sa.String(50), nullable=False, server_default="UNKNOWN", comment="Discrete estimated direction"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0", comment="Mean pose/landmark confidence during event"),
        sa.Column("visit_number", sa.Integer(), nullable=False, server_default="1", comment="Visit count for repeated attention tracking"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analysis_id"], ["attention_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["ai_jobs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_attention_events_analysis_id", "attention_events", ["analysis_id"])
    op.create_index("ix_attention_events_job_id", "attention_events", ["job_id"])
    op.create_index("ix_attention_events_track_id", "attention_events", ["track_id"])
    op.create_index("ix_attention_events_target_id", "attention_events", ["target_id"])


def downgrade() -> None:
    op.drop_index("ix_attention_events_target_id", table_name="attention_events")
    op.drop_index("ix_attention_events_track_id", table_name="attention_events")
    op.drop_index("ix_attention_events_job_id", table_name="attention_events")
    op.drop_index("ix_attention_events_analysis_id", table_name="attention_events")
    op.drop_table("attention_events")

    op.drop_index("ix_attention_analyses_store_id", table_name="attention_analyses")
    op.drop_index("ix_attention_analyses_camera_id", table_name="attention_analyses")
    op.drop_index("ix_attention_analyses_job_id", table_name="attention_analyses")
    op.drop_table("attention_analyses")
