"""
User Routes
============
Handles user profile retrieval, updates, and admin user listing.
All routes are protected — require a valid JWT token.

Endpoints:
    GET    /api/users/            List all users (admin only)
    GET    /api/users/profile     Get current user's profile
    PUT    /api/users/profile     Update current user's profile
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdateRequest
from app.middleware.jwt_auth import get_current_user
from app.core.dependencies import admin_only

router = APIRouter(prefix="/api/users", tags=["Users"])


# ── List All Users (Admin Only) ───────────────────────────────
@router.get(
    "",
    summary="List all users with role statistics (admin only)",
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Insufficient permissions"},
    },
)
def list_users(
    current_user: User = Depends(admin_only),
    db: Session = Depends(get_db),
):
    """
    Returns a list of all users with their roles, plus aggregate
    role statistics. Restricted to Administrator role.
    """
    from sqlalchemy import func
    from app.models.role import Role

    users = db.query(User).all()

    # Aggregate role counts
    role_counts_query = (
        db.query(Role.role_name, func.count(User.id))
        .join(User, User.role_id == Role.id)
        .group_by(Role.role_name)
        .all()
    )
    role_stats = {name: count for name, count in role_counts_query}

    user_list = [
        {
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "role": u.role.role_name if u.role else "Unknown",
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]

    return {
        "users": user_list,
        "total": len(user_list),
        "role_stats": role_stats,
    }


# ── Get Profile ───────────────────────────────────────────────
@router.get(
    "/profile",
    response_model=UserResponse,
    summary="Get current user's profile",
    responses={
        401: {"description": "Not authenticated"},
    },
)
def get_profile(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the full profile of the currently authenticated user.
    Includes role information.
    """
    return current_user


# ── Update Profile ────────────────────────────────────────────
@router.put(
    "/profile",
    response_model=UserResponse,
    summary="Update current user's profile",
    responses={
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
def update_profile(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.
    Only `full_name` and `phone` can be updated.
    Email and role changes are not allowed through this endpoint.
    """
    # Apply only the fields that were provided
    if payload.full_name is not None:
        current_user.full_name = payload.full_name

    if payload.phone is not None:
        current_user.phone = payload.phone

    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_user)

    return current_user
