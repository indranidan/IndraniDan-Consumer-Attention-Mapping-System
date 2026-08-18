"""Add input_type column to ai_jobs table

Revision ID: 004
Revises: 003
Create Date: 2026-08-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_jobs",
        sa.Column(
            "input_type",
            sa.String(20),
            nullable=False,
            server_default="VIDEO_FILE",
            comment="Input source type: VIDEO_FILE, WEBCAM, FUTURE_CAMERA",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_jobs", "input_type")
