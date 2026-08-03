"""
Password Hashing Utilities
===========================
Provides bcrypt-based password hashing and verification.
Uses passlib's CryptContext for a clean, swappable interface.
"""

from passlib.context import CryptContext

# ── CryptContext Configuration ────────────────────────────────
# "bcrypt" is the primary scheme; deprecated="auto" will automatically
# re-hash passwords if we ever add a new scheme in the future.
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """
    Hash a plain-text password using bcrypt.

    Args:
        plain_password: The raw password string to hash.

    Returns:
        A bcrypt hash string safe for database storage.
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a bcrypt hash.

    Args:
        plain_password: The raw password to check.
        hashed_password: The stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)
