"""Password hashing and verification helpers backed by bcrypt."""

from __future__ import annotations

import bcrypt

BCRYPT_ROUNDS: int = 10
BCRYPT_MAX_BYTES: int = 72


def _encode(password: str) -> bytes:
    """Encode a password and truncate it to bcrypt's 72 byte limit.

    Args:
        password: The plaintext password.

    Returns:
        bytes: The UTF-8 encoded password, truncated when too long.
    """
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str, rounds: int = BCRYPT_ROUNDS) -> str:
    """Hash a plaintext password with a generated salt.

    Args:
        password: The plaintext password.
        rounds: Salt rounds / cost factor. Defaults to
            :data:`BCRYPT_ROUNDS` (10).

    Returns:
        str: The bcrypt hash, safe to store in the database.

    Raises:
        ValueError: If the password is empty or ``rounds`` is out of range.
    """
    if not password:
        raise ValueError("Password must not be empty")
    if not 4 <= rounds <= 31:
        raise ValueError("rounds must be between 4 and 31")
    hashed: bytes = bcrypt.hashpw(_encode(password), bcrypt.gensalt(rounds=rounds))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare a plaintext password against a stored hash.

    Args:
        plain_password: The plaintext password supplied by the user.
        hashed_password: The bcrypt hash stored in the database.

    Returns:
        bool: ``True`` when the password matches, ``False`` otherwise.
        Malformed hashes and empty inputs also return ``False`` instead of
        raising, so a corrupted row cannot break the login endpoint.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(_encode(plain_password), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False