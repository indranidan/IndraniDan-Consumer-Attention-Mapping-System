"""
JWT Authentication Middleware
==============================
FastAPI dependencies for:
  1. Extracting and validating the current user from a Bearer token.
  2. Enforcing role-based access control on protected routes.
"""

import uuid
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.user import User
from app.utils.token import decode_access_token

# ── OAuth2 scheme ─────────────────────────────────────────────
# tokenUrl points to our login endpoint for Swagger UI integration.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts the current authenticated user
    from the Bearer token in the Authorization header.

    Steps:
        1. Decode the JWT token
        2. Extract user_id from payload
        3. Fetch the user from the database
        4. Verify the account is active

    Raises:
        HTTPException 401: Invalid/expired token or user not found
        HTTPException 403: Account is disabled

    Usage:
        @router.get("/protected")
        def protected_route(user: User = Depends(get_current_user)):
            ...
    """
    payload = decode_access_token(token)

    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user_id.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: malformed user_id.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Token may be stale.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact an administrator.",
        )

    return user


def require_roles(*allowed_roles: str) -> Callable:
    """
    Dependency factory for role-based access control.

    Creates a FastAPI dependency that checks if the current user
    has one of the allowed roles. If not, raises 403 Forbidden.

    Args:
        *allowed_roles: One or more role name strings.
                        e.g., require_roles("Administrator", "Store Manager")

    Returns:
        A FastAPI dependency function.

    Usage:
        @router.get(
            "/admin-only",
            dependencies=[Depends(require_roles("Administrator"))],
        )
        def admin_endpoint():
            ...
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role.role_name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(allowed_roles)}. "
                       f"Your role: {current_user.role.role_name}.",
            )
        return current_user

    return role_checker
