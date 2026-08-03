"""
Authentication Service
=======================
Business logic for user registration, login, and Google OAuth.
Keeps route handlers thin by centralizing auth logic here.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.role import Role
from app.schemas.auth import RegisterRequest, UserBrief
from app.utils.password import hash_password, verify_password
from app.utils.token import create_access_token


# ── Role name constants (match seeded data) ───────────────────
ROLE_ADMINISTRATOR = "Administrator"
ROLE_STORE_MANAGER = "Store Manager"
ROLE_RETAIL_ANALYST = "Retail Analyst"
ROLE_MARKETING_MANAGER = "Marketing Manager"


def get_role_by_id(db: Session, role_id: uuid.UUID) -> Role:
    """
    Fetch a role by its UUID. Raises 404 if not found.
    """
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id '{role_id}' not found.",
        )
    return role


def get_all_roles(db: Session) -> list[Role]:
    """Fetch all available roles."""
    return db.query(Role).order_by(Role.role_name).all()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Fetch a user by email address. Returns None if not found."""
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User:
    """
    Fetch a user by their UUID. Raises 404 if not found.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def register_user(db: Session, payload: RegisterRequest) -> User:
    """
    Register a new user.

    Steps:
        1. Check email uniqueness → 409 if duplicate
        2. Validate that the role exists → 404 if not
        3. Hash the password
        4. Create and persist the User record

    Returns:
        The newly created User object.
    """
    # Check for duplicate email
    existing = get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email address already exists.",
        )

    # Validate role exists
    role = get_role_by_id(db, payload.role_id)

    # Create user with hashed password
    user = User(
        id=uuid.uuid4(),
        full_name=payload.full_name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        phone=payload.phone,
        role_id=role.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(db: Session, email: str, password: str) -> dict:
    """
    Authenticate a user with email and password.

    Steps:
        1. Find user by email → 401 if not found
        2. Check if account is active → 403 if disabled
        3. Verify password → 401 if wrong
        4. Generate JWT with user_id, email, role

    Returns:
        Dict with access_token, token_type, and user brief.
    """
    user = get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact an administrator.",
        )

    # OAuth-only users don't have a password
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account uses Google login. Please sign in with Google.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate JWT token
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.role_name,
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserBrief(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role.role_name,
        ),
    }


def get_or_create_google_user(
    db: Session,
    email: str,
    full_name: str,
) -> dict:
    """
    Handle Google OAuth login/registration.

    If the user exists, log them in.
    If not, create a new account with the default 'Retail Analyst' role
    (no password since they authenticate via Google).

    Returns:
        Dict with access_token, token_type, and user brief.
    """
    user = get_user_by_email(db, email)

    if not user:
        # Find the default role for OAuth users
        default_role = (
            db.query(Role)
            .filter(Role.role_name == ROLE_RETAIL_ANALYST)
            .first()
        )
        if not default_role:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default role not found. Please run database migrations.",
            )

        user = User(
            id=uuid.uuid4(),
            full_name=full_name,
            email=email,
            password_hash=None,  # OAuth users don't have a local password
            phone=None,
            role_id=default_role.id,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact an administrator.",
        )

    # Generate JWT token
    token_data = {
        "user_id": str(user.id),
        "email": user.email,
        "role": user.role.role_name,
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserBrief(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            role=user.role.role_name,
        ),
    }
