"""
User Schemas
=============
Pydantic models for user profile responses and update requests.
"""

import re
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class RoleResponse(BaseModel):
    """Schema for role information."""

    id: uuid.UUID
    role_name: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for full user profile response."""

    id: uuid.UUID
    full_name: str
    email: str
    phone: str | None
    role: RoleResponse
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """Schema for updating user profile (name and phone only)."""

    full_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
        examples=["Jane Doe"],
        description="Updated full name",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        examples=["+1234567890"],
        description="Updated phone number",
    )

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate phone number format."""
        if v is not None:
            cleaned = v.strip()
            if cleaned and not re.match(r"^\+?[\d\s\-()]{7,20}$", cleaned):
                raise ValueError(
                    "Invalid phone number format. Use digits, spaces, dashes, or parentheses."
                )
            return cleaned
        return v
