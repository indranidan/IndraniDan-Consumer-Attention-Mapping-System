"""
Dashboard Routes
================
Simple management dashboard statistics.

Endpoints:
    GET    /api/dashboard/stats    Get entity counts
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database.database import get_db
from app.models.user import User
from app.models.store import Store
from app.models.zone import Zone
from app.models.shelf import Shelf
from app.models.product import Product
from app.models.camera import Camera
from app.core.dependencies import any_role

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class DashboardStats(BaseModel):
    """Dashboard statistics response."""
    stores: int
    zones: int
    shelves: int
    products: int
    cameras: int


@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    responses={
        401: {"description": "Not authenticated"},
    },
)
def get_dashboard_stats(
    current_user: User = Depends(any_role),
    db: Session = Depends(get_db),
):
    """
    Returns counts of all managed entities.
    Available to all authenticated users.
    """
    return DashboardStats(
        stores=db.query(Store).count(),
        zones=db.query(Zone).count(),
        shelves=db.query(Shelf).count(),
        products=db.query(Product).count(),
        cameras=db.query(Camera).count(),
    )
