"""
User Model
==========
Represents a system user with authentication credentials, profile info,
and a foreign key to their assigned role.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class User(Base):
    """
    Users table — stores all registered users.

    Notes:
        - email is unique and indexed for fast lookups during login.
        - password_hash is nullable to support Google OAuth users who
          authenticate without a local password.
        - is_active defaults to True; can be set False to disable accounts.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="User's full display name",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Login email — must be unique",
    )
    password_hash: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="bcrypt hash; NULL for OAuth-only users",
    )
    phone: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Optional phone number",
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="FK to the user's assigned role",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Soft-delete flag; inactive users cannot log in",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    role: Mapped["Role"] = relationship(  # noqa: F821
        "Role",
        back_populates="users",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role_id}')>"
