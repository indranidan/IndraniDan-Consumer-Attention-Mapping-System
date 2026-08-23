"""add_zone_config_to_ai_jobs

Revision ID: 008
Revises: 007
Create Date: 2026-08-22
"""
from typing import Sequence, Union

from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_jobs",
        sa.Column(
            "zone_config",
            sa.JSON(),
            nullable=True,
            comment="Custom calibrated video zones and regions JSON",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_jobs", "zone_config")
