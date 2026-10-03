"""JWT token generation and verification helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

from app.config import settings
from app.utils.exceptions import AuthenticationError


def create_access_token(
    subject: str | int,
    *,
    role: str | None = None,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed JWT for the given subject.

    Args:
        subject: Identifier stored in the ``sub`` claim, usually the user id.
        role: Optional role claim used for authorization checks.
        expires_delta: Custom token lifetime, defaults to the configured one.
        additional_claims: Extra claims merged into the payload.

    Returns:
        str: The encoded JWT.
    """
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta if expires_delta is not None else timedelta(seconds=settings.jwt_expiry_seconds)
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
    }
    if role is not None:
        payload["role"] = role
    if additional_claims:
        payload.update(additional_claims)

    token: str = jwt.encode(payload, settings.jwt_secret, algorithm=settings.algorithm)
    return token


def decode_token(token: str, *, verify_exp: bool = True) -> Dict[str, Any]:
    """Decode and validate a JWT.

    Args:
        token: The encoded token to validate.
        verify_exp: Whether the ``exp`` claim must be valid.

    Returns:
        dict: The decoded payload.

    Raises:
        AuthenticationError: If the token is expired, malformed or invalid.
    """
    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.algorithm],
            issuer=settings.jwt_issuer,
            options={"verify_exp": verify_exp},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token has expired", code="token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid authentication token", code="invalid_token") from exc