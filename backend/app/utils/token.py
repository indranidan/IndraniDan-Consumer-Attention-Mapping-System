"""
JWT Token Utilities
====================
Provides functions for creating and decoding JWT access tokens.
Tokens include user_id, email, and role in the payload.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import HTTPException, status

from app.core.config import get_settings

settings = get_settings()


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload data to encode. Should include:
              - user_id (str): UUID of the user
              - email (str): User's email
              - role (str): User's role name
        expires_delta: Optional custom expiration. Defaults to
                       ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string.

    Returns:
        Decoded payload dictionary containing user_id, email, role.

    Raises:
        HTTPException 401: If the token is expired, invalid, or
                           missing required claims.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        # Validate required claims exist
        user_id: str | None = payload.get("user_id")
        email: str | None = payload.get("email")
        role: str | None = payload.get("role")

        if user_id is None or email is None or role is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token payload is missing required claims.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
