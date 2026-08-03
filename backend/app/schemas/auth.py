"""
Authentication Schemas
=======================
Pydantic models for registration, login, and token responses.
Includes strong password validation and email format checking.
"""

import re
import uuid
from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Schema for user registration."""

    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        examples=["John Doe"],
        description="User's full display name",
    )
    email: EmailStr = Field(
        ...,
        examples=["john.doe@example.com"],
        description="Unique login email address",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["StrongP@ss1"],
        description="Password (min 8 chars, must include upper, lower, digit, special)",
    )
    phone: str | None = Field(
        default=None,
        max_length=20,
        examples=["+1234567890"],
        description="Optional phone number",
    )
    role_id: uuid.UUID = Field(
        ...,
        description="UUID of the role to assign to the user",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Enforce strong password policy:
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character
        """
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit.")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/~`]", v):
            raise ValueError("Password must contain at least one special character.")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate phone number format (digits, spaces, dashes, plus sign)."""
        if v is not None:
            cleaned = v.strip()
            if cleaned and not re.match(r"^\+?[\d\s\-()]{7,20}$", cleaned):
                raise ValueError(
                    "Invalid phone number format. Use digits, spaces, dashes, or parentheses."
                )
            return cleaned
        return v


class LoginRequest(BaseModel):
    """Schema for user login."""

    email: EmailStr = Field(
        ...,
        examples=["john.doe@example.com"],
        description="Registered email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        examples=["StrongP@ss1"],
        description="Account password",
    )


class TokenResponse(BaseModel):
    """Schema for JWT token response after successful authentication."""

    access_token: str = Field(
        ...,
        description="JWT access token",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )
    user: "UserBrief" = Field(
        ...,
        description="Basic user information",
    )


class UserBrief(BaseModel):
    """Minimal user info returned with the token."""

    id: uuid.UUID
    full_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
