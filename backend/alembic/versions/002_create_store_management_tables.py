"""Create store management tables (stores, zones, shelves, products, cameras)

Revision ID: 002
Revises: 001
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Create stores table ──────────────────────────────────
    op.create_table(
        "stores",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False, comment="Store display name"),
        sa.Column("store_code", sa.String(50), nullable=False, comment="Unique store identifier code"),
        sa.Column("address", sa.String(500), nullable=True, comment="Street address"),
        sa.Column("city", sa.String(100), nullable=True, comment="City name"),
        sa.Column("state", sa.String(100), nullable=True, comment="State or province"),
        sa.Column("country", sa.String(100), nullable=True, comment="Country name"),
        sa.Column("postal_code", sa.String(20), nullable=True, comment="Postal or ZIP code"),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional store description"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="Store status: active or inactive"),
        sa.Column("created_by", sa.Uuid(), nullable=False, comment="FK to the user who created this store"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_code"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_stores_store_code", "stores", ["store_code"])
    op.create_index("ix_stores_created_by", "stores", ["created_by"])

    # ── Create zones table ───────────────────────────────────
    op.create_table(
        "zones",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False, comment="FK to the parent store"),
        sa.Column("name", sa.String(200), nullable=False, comment="Zone display name"),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional zone description"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_zones_store_id", "zones", ["store_id"])

    # ── Create shelves table ─────────────────────────────────
    op.create_table(
        "shelves",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False, comment="FK to the parent store"),
        sa.Column("zone_id", sa.Uuid(), nullable=False, comment="FK to the parent zone"),
        sa.Column("name", sa.String(200), nullable=False, comment="Shelf display name"),
        sa.Column("shelf_code", sa.String(50), nullable=False, comment="Unique shelf identifier code"),
        sa.Column("category", sa.String(100), nullable=True, comment="Product category for this shelf"),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional shelf description"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shelf_code"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_shelves_store_id", "shelves", ["store_id"])
    op.create_index("ix_shelves_zone_id", "shelves", ["zone_id"])
    op.create_index("ix_shelves_shelf_code", "shelves", ["shelf_code"])

    # ── Create products table ────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False, comment="FK to the parent store"),
        sa.Column("zone_id", sa.Uuid(), nullable=False, comment="FK to the parent zone"),
        sa.Column("shelf_id", sa.Uuid(), nullable=False, comment="FK to the parent shelf"),
        sa.Column("name", sa.String(200), nullable=False, comment="Product display name"),
        sa.Column("sku", sa.String(100), nullable=False, comment="Unique Stock Keeping Unit code"),
        sa.Column("brand", sa.String(150), nullable=True, comment="Product brand name"),
        sa.Column("category", sa.String(100), nullable=True, comment="Product category"),
        sa.Column("price", sa.Numeric(10, 2), nullable=True, comment="Product price"),
        sa.Column("description", sa.Text(), nullable=True, comment="Optional product description"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["shelf_id"], ["shelves.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_products_store_id", "products", ["store_id"])
    op.create_index("ix_products_zone_id", "products", ["zone_id"])
    op.create_index("ix_products_shelf_id", "products", ["shelf_id"])
    op.create_index("ix_products_sku", "products", ["sku"])

    # ── Create cameras table ─────────────────────────────────
    op.create_table(
        "cameras",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("store_id", sa.Uuid(), nullable=False, comment="FK to the parent store"),
        sa.Column("zone_id", sa.Uuid(), nullable=True, comment="FK to the optional parent zone"),
        sa.Column("name", sa.String(200), nullable=False, comment="Camera display name"),
        sa.Column("camera_source", sa.String(500), nullable=False, comment="Camera feed URL or device identifier"),
        sa.Column("location_description", sa.Text(), nullable=True, comment="Description of camera placement"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active", comment="Camera status: active, inactive, or maintenance"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["zone_id"], ["zones.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_cameras_store_id", "cameras", ["store_id"])
    op.create_index("ix_cameras_zone_id", "cameras", ["zone_id"])


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("ix_cameras_zone_id", table_name="cameras")
    op.drop_index("ix_cameras_store_id", table_name="cameras")
    op.drop_table("cameras")

    op.drop_index("ix_products_sku", table_name="products")
    op.drop_index("ix_products_shelf_id", table_name="products")
    op.drop_index("ix_products_zone_id", table_name="products")
    op.drop_index("ix_products_store_id", table_name="products")
    op.drop_table("products")

    op.drop_index("ix_shelves_shelf_code", table_name="shelves")
    op.drop_index("ix_shelves_zone_id", table_name="shelves")
    op.drop_index("ix_shelves_store_id", table_name="shelves")
    op.drop_table("shelves")

    op.drop_index("ix_zones_store_id", table_name="zones")
    op.drop_table("zones")

    op.drop_index("ix_stores_created_by", table_name="stores")
    op.drop_index("ix_stores_store_code", table_name="stores")
    op.drop_table("stores")
