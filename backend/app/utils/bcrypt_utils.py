"""Password hashing and verification helpers backed by bcrypt."""

from __future__ import annotations

import bcrypt

BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    """Encode a password and truncate it to bcrypt's 72 byte limit.

    Args:
        password: The plaintext password.

    Returns:
        bytes: The UTF-8 encoded password, truncated when too long.
    """
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: The plaintext password.

    Returns:
        str: The bcrypt hash, safe to store in the database.
    """
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plaintext password against a stored hash.

    Args:
        password: The plaintext password supplied by the user.
        password_hash: The bcrypt hash stored in the database.

    Returns:
        bool: ``True`` when the password matches, ``False`` otherwise.
    """
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(_prepare(password), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False