"""Create AI jobs table

Revision ID: 003
Revises: 002
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create ai_jobs table ────────────────────────────────
    op.create_table(
        "ai_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "camera_id", sa.Uuid(), nullable=False,
            comment="FK to the camera being analyzed",
        ),
        sa.Column(
            "store_id", sa.Uuid(), nullable=False,
            comment="FK to the parent store",
        ),
        sa.Column(
            "source", sa.String(500), nullable=False,
            comment="Video source path or camera feed URL used for analysis",
        ),
        sa.Column(
            "status", sa.String(20), nullable=False,
            server_default="QUEUED",
            comment="Job status: QUEUED, RUNNING, COMPLETED, FAILED, STOPPED",
        ),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=True,
            comment="Timestamp when processing started",
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True,
            comment="Timestamp when processing completed or failed",
        ),
        sa.Column(
            "error_message", sa.Text(), nullable=True,
            comment="Error details if job failed",
        ),
        sa.Column(
            "output_path", sa.String(500), nullable=True,
            comment="Relative path to job output directory",
        ),
        sa.Column(
            "summary", sa.JSON(), nullable=True,
            comment="Compact analytics summary JSON after completion",
        ),
        sa.Column(
            "created_by", sa.Uuid(), nullable=False,
            comment="FK to the user who created this job",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["camera_id"], ["cameras.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["store_id"], ["stores.id"], ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_ai_jobs_camera_id", "ai_jobs", ["camera_id"])
    op.create_index("ix_ai_jobs_store_id", "ai_jobs", ["store_id"])
    op.create_index("ix_ai_jobs_status", "ai_jobs", ["status"])
    op.create_index("ix_ai_jobs_created_by", "ai_jobs", ["created_by"])


def downgrade() -> None:
    op.drop_index("ix_ai_jobs_created_by", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_status", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_store_id", table_name="ai_jobs")
    op.drop_index("ix_ai_jobs_camera_id", table_name="ai_jobs")
    op.drop_table("ai_jobs")
