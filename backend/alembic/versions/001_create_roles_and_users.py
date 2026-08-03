"""Create roles and users tables with seed data

Revision ID: 001
Revises: None
Create Date: 2026-07-26
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# ── Predefined role UUIDs (stable for FK references & testing) ──
ROLE_ADMINISTRATOR = uuid.UUID("a1000000-0000-0000-0000-000000000001")
ROLE_STORE_MANAGER = uuid.UUID("a1000000-0000-0000-0000-000000000002")
ROLE_RETAIL_ANALYST = uuid.UUID("a1000000-0000-0000-0000-000000000003")
ROLE_MARKETING_MANAGER = uuid.UUID("a1000000-0000-0000-0000-000000000004")


def upgrade() -> None:
    # ── Create roles table ────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_name", sa.String(50), nullable=False, comment="Unique role name (e.g., Administrator)"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_name"),
    )
    op.create_index("ix_roles_role_name", "roles", ["role_name"])

    # ── Create users table ────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False, comment="User's full display name"),
        sa.Column("email", sa.String(255), nullable=False, comment="Login email — must be unique"),
        sa.Column("password_hash", sa.Text(), nullable=True, comment="bcrypt hash; NULL for OAuth-only users"),
        sa.Column("phone", sa.String(20), nullable=True, comment="Optional phone number"),
        sa.Column("role_id", sa.Uuid(), nullable=False, comment="FK to the user's assigned role"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role_id", "users", ["role_id"])

    # ── Seed predefined roles ─────────────────────────────────
    now = datetime.now(timezone.utc)
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("role_name", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(roles_table, [
        {"id": ROLE_ADMINISTRATOR, "role_name": "Administrator", "created_at": now},
        {"id": ROLE_STORE_MANAGER, "role_name": "Store Manager", "created_at": now},
        {"id": ROLE_RETAIL_ANALYST, "role_name": "Retail Analyst", "created_at": now},
        {"id": ROLE_MARKETING_MANAGER, "role_name": "Marketing Manager", "created_at": now},
    ])


def downgrade() -> None:
    op.drop_index("ix_users_role_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_index("ix_roles_role_name", table_name="roles")
    op.drop_table("roles")
