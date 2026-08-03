"""
User Routes
============
Handles user profile retrieval and updates.
All routes are protected — require a valid JWT token.

Endpoints:
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

router = APIRouter(prefix="/api/users", tags=["Users"])


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
