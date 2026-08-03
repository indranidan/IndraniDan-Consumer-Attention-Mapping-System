"""
Role Model
==========
Represents a user role in the system (e.g., Administrator, Store Manager).
Each user belongs to exactly one role.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class Role(Base):
    """
    Roles table — stores the predefined user roles.

    Predefined roles (seeded via migration):
        - Administrator
        - Store Manager
        - Retail Analyst
        - Marketing Manager
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )
    role_name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique role name (e.g., Administrator)",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User",
        back_populates="role",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, role_name='{self.role_name}')>"
