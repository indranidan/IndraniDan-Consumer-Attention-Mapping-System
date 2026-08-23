"""drop_retired_ai_tables

Revision ID: 007
Revises: 006
Create Date: 2026-08-22
"""
from typing import Sequence, Union
from alembic import op
# pyrefly: ignore [missing-import]
import sqlalchemy as sa

revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RETIRED_TABLES = [
    # Module 5 interaction tables
    'product_comparison_events',
    'shelf_interaction_metrics',
    'product_engagement_metrics',
    'product_interaction_events',
    'product_interaction_analyses',
    # Module 4 attention tables
    'target_attention_summaries',
    'shelf_attention_summaries',
    'attention_events',
    'attention_analyses',
]


def upgrade() -> None:
    conn = op.get_bind()
    for table_name in RETIRED_TABLES:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))


def downgrade() -> None:
    # AI analytical data is now persisted in MongoDB; legacy relational tables are deprecated.
    pass
