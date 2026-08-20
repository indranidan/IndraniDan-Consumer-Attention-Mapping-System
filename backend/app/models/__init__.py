"""
Models Package
==============
Re-exports all SQLAlchemy models so Alembic can auto-detect them
by simply importing this package.
"""

from app.models.role import Role
from app.models.user import User
from app.models.store import Store
from app.models.zone import Zone
from app.models.shelf import Shelf
from app.models.product import Product
from app.models.camera import Camera
from app.models.ai_job import AIJob
from app.models.attention import AttentionAnalysis, AttentionEventModel

__all__ = [
    "Role",
    "User",
    "Store",
    "Zone",
    "Shelf",
    "Product",
    "Camera",
    "AIJob",
    "AttentionAnalysis",
    "AttentionEventModel",
]

