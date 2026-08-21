"""Create Module 5 product interaction tables (product_interaction_analyses, product_interaction_events)

Revision ID: 006
Revises: 005
Create Date: 2026-08-21
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create product_interaction_analyses table ─────────────
    op.create_table(
        "product_interaction_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="FK to parent AI job"),
        sa.Column("camera_id", sa.Uuid(), nullable=False, comment="FK to camera"),
        sa.Column("store_id", sa.Uuid(), nullable=False, comment="FK to store"),
        sa.Column("total_views", sa.Integer(), nullable=False, server_default="0", comment="Total product view events"),
        sa.Column("total_pickups", sa.Integer(), nullable=False, server_default="0", comment="Total verified product pickup events"),
        sa.Column("total_returns", sa.Integer(), nullable=False, server_default="0", comment="Total verified product return events"),
        sa.Column("total_comparisons", sa.Integer(), nullable=False, server_default="0", comment="Total multi-product comparison patterns observed"),
        sa.Column("total_purchases", sa.Integer(), nullable=False, server_default="0", comment="Total purchases from POS (0 if unconfigured)"),
        sa.Column("total_unique_viewers", sa.Integer(), nullable=False, server_default="0", comment="Total unique shopper tracking IDs who viewed products/shelves"),
        sa.Column("total_engagement_duration_sec", sa.Float(), nullable=False, server_default="0.0", comment="Cumulative engagement duration in seconds"),
        sa.Column("pickup_detection_status", sa.String(100), nullable=False, server_default="INSUFFICIENT_VISUAL_EVIDENCE", comment="Status of pickup visual evidence"),
        sa.Column("purchase_data_status", sa.String(100), nullable=False, server_default="UNAVAILABLE / NOT CONFIGURED (No POS Data)", comment="Status of purchase transaction integration"),
        sa.Column("product_metrics", sa.JSON(), nullable=True, comment="JSON array of per-product engagement metrics"),
        sa.Column("shelf_metrics", sa.JSON(), nullable=True, comment="JSON array of per-shelf interaction metrics"),
        sa.Column("comparison_patterns", sa.JSON(), nullable=True, comment="JSON array of multi-product comparison sequences"),
        sa.Column("summary_data", sa.JSON(), nullable=True, comment="Full summary payload for Module 5"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
        sa.ForeignKeyConstraint(["job_id"], ["ai_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_interaction_analyses_job_id", "product_interaction_analyses", ["job_id"])
    op.create_index("ix_product_interaction_analyses_camera_id", "product_interaction_analyses", ["camera_id"])
    op.create_index("ix_product_interaction_analyses_store_id", "product_interaction_analyses", ["store_id"])

    # ── Create product_interaction_events table ───────────────
    op.create_table(
        "product_interaction_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False, comment="FK to parent product interaction analysis"),
        sa.Column("job_id", sa.Uuid(), nullable=False, comment="FK to parent AI job"),
        sa.Column("event_id", sa.String(100), nullable=False, comment="Unique event identifier string"),
        sa.Column("event_type", sa.String(50), nullable=False, comment="PRODUCT_VIEWED, PRODUCT_PICKED_UP, PRODUCT_RETURNED, PRODUCT_PURCHASED, PRODUCT_COMPARED"),
        sa.Column("track_id", sa.Integer(), nullable=False, comment="ByteTrack tracking ID"),
        sa.Column("session_id", sa.String(100), nullable=True, comment="Associated session ID"),
        sa.Column("product_id", sa.String(100), nullable=True, comment="Associated product ID or code"),
        sa.Column("product_name", sa.String(200), nullable=True, comment="Product display name"),
        sa.Column("sku", sa.String(100), nullable=True, comment="Stock Keeping Unit code"),
        sa.Column("shelf_id", sa.String(100), nullable=True, comment="Shelf identifier code"),
        sa.Column("shelf_name", sa.String(200), nullable=True, comment="Shelf display name"),
        sa.Column("camera_id", sa.Uuid(), nullable=True, comment="FK to camera"),
        sa.Column("store_id", sa.Uuid(), nullable=True, comment="FK to store"),
        sa.Column("timestamp", sa.Float(), nullable=False, comment="Start timestamp in seconds into video"),
        sa.Column("start_time", sa.Float(), nullable=False, comment="Event start timestamp in seconds"),
        sa.Column("end_time", sa.Float(), nullable=True, comment="Event end timestamp in seconds"),
        sa.Column("duration_seconds", sa.Float(), nullable=False, server_default="0.0", comment="Event duration in seconds"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0", comment="Detection confidence score (0.0 to 1.0)"),
        sa.Column("source", sa.String(50), nullable=False, server_default="MODULE_4_ATTENTION", comment="Source of event"),
        sa.Column("metadata_json", sa.JSON(), nullable=True, comment="Extra metadata such as comparison sequences, bounding boxes, or verification notes"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analysis_id"], ["product_interaction_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["ai_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_product_interaction_events_analysis_id", "product_interaction_events", ["analysis_id"])
    op.create_index("ix_product_interaction_events_job_id", "product_interaction_events", ["job_id"])
    op.create_index("ix_product_interaction_events_event_id", "product_interaction_events", ["event_id"])
    op.create_index("ix_product_interaction_events_event_type", "product_interaction_events", ["event_type"])
    op.create_index("ix_product_interaction_events_track_id", "product_interaction_events", ["track_id"])
    op.create_index("ix_product_interaction_events_product_id", "product_interaction_events", ["product_id"])
    op.create_index("ix_product_interaction_events_shelf_id", "product_interaction_events", ["shelf_id"])


def downgrade() -> None:
    op.drop_index("ix_product_interaction_events_shelf_id", table_name="product_interaction_events")
    op.drop_index("ix_product_interaction_events_product_id", table_name="product_interaction_events")
    op.drop_index("ix_product_interaction_events_track_id", table_name="product_interaction_events")
    op.drop_index("ix_product_interaction_events_event_type", table_name="product_interaction_events")
    op.drop_index("ix_product_interaction_events_event_id", table_name="product_interaction_events")
    op.drop_index("ix_product_interaction_events_job_id", table_name="product_interaction_events")
    op.drop_index("ix_product_interaction_events_analysis_id", table_name="product_interaction_events")
    op.drop_table("product_interaction_events")

    op.drop_index("ix_product_interaction_analyses_store_id", table_name="product_interaction_analyses")
    op.drop_index("ix_product_interaction_analyses_camera_id", table_name="product_interaction_analyses")
    op.drop_index("ix_product_interaction_analyses_job_id", table_name="product_interaction_analyses")
    op.drop_table("product_interaction_analyses")
