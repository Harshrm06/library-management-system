"""JWT helpers: token creation, verification and decoding.

Invalid or expired tokens are converted into :class:`UnauthorizedError` so the
API answers with a 401 JSON payload; the original PyJWT exception is always
chained as ``__cause__`` for logging.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

import jwt

from app.config import settings
from app.utils.exceptions import UnauthorizedError

DEFAULT_EXPIRY = timedelta(hours=24)


def create_access_token(
    data: Mapping[str, Any],
    expires_delta: Optional[timedelta] = None,
    **extra_claims: Any,
) -> str:
    """Create a signed HS256 access token.

    Args:
        data: Claims to embed. ``user_id`` is also copied into ``sub`` so the
            token can be resolved back to a user. ``email`` and ``role`` are
            optional.
        expires_delta: Token lifetime; defaults to
            ``JWT_EXPIRY_HOURS`` (24 hours) from the settings.
        **extra_claims: Additional claims merged into the payload.

    Returns:
        str: The encoded JWT.

    Raises:
        UnauthorizedError: If ``user_id`` is missing from ``data``.

    Example:
        >>> token = create_access_token({"user_id": 1, "email": "a@b.c", "role": "member"})
    """
    if not data or data.get("user_id") is None:
        raise UnauthorizedError(
            "Token payload requires a user_id",
            detail="create_access_token expects a mapping containing 'user_id'.",
            code="invalid_token_payload",
        )

    now: datetime = datetime.now(timezone.utc)
    lifetime: timedelta = expires_delta if expires_delta is not None else DEFAULT_EXPIRY
    expires_at: datetime = now + lifetime

    payload: Dict[str, Any] = {
        "sub": str(data["user_id"]),
        "user_id": data["user_id"],
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.jwt_issuer,
        "jti": uuid.uuid4().hex,
    }
    for claim in ("email", "role"):
        value: Any = data.get(claim)
        if value is not None:
            payload[claim] = value.value if hasattr(value, "value") else value
    payload.update(extra_claims)

    token: str = jwt.encode(payload, settings.jwt_secret, algorithm=settings.algorithm)
    return token


def verify_token(token: str, *, verify_exp: bool = True) -> Dict[str, Any]:
    """Validate a JWT and return its payload.

    Args:
        token: The encoded token to validate.
        verify_exp: Whether the ``exp`` claim must be valid.

    Returns:
        dict: The decoded payload containing ``user_id``, ``email`` and
        ``role``.

    Raises:
        UnauthorizedError: If the token is missing, expired
            (``code="token_expired"``), malformed or otherwise invalid
            (``code="invalid_token"``).
    """
    if not token or not isinstance(token, str):
        raise UnauthorizedError(
            "Missing authentication token",
            detail="A bearer token is required to access this resource.",
            code="missing_token",
        )

    try:
        payload: Dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.algorithm],
            issuer=settings.jwt_issuer,
            options={"verify_exp": verify_exp},
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError(
            "Token has expired",
            detail="The access token is no longer valid; request a new one.",
            code="token_expired",
        ) from exc
    except jwt.DecodeError as exc:
        raise UnauthorizedError(
            "Invalid authentication token",
            detail="The token could not be decoded.",
            code="invalid_token",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(
            "Invalid authentication token",
            detail="The token failed signature or claim validation.",
            code="invalid_token",
        ) from exc

    if payload.get("user_id") is None and payload.get("sub") is not None:
        payload["user_id"] = payload["sub"]
    return payload


def decode_token(token: str, *, verify_exp: bool = True) -> Dict[str, Any]:
    """Decode a JWT; middleware-facing alias of :func:`verify_token`.

    Args:
        token: The encoded token to decode.
        verify_exp: Whether the ``exp`` claim must be valid.

    Returns:
        dict: The decoded payload.

    Raises:
        UnauthorizedError: If the token is missing, expired or invalid.
    """
    return verify_token(token, verify_exp=verify_exp)


def token_expiry_datetime(token: str) -> datetime:
    """Return the expiry moment of a token as a naive UTC datetime.

    Args:
        token: A valid, non-expired access token.

    Returns:
        datetime: The ``exp`` claim converted to naive UTC.

    Raises:
        UnauthorizedError: If the token is missing, expired or invalid.
    """
    payload: Dict[str, Any] = verify_token(token)
    exp: Any = payload.get("exp")
    if exp is None:
        raise UnauthorizedError(
            "Invalid authentication token",
            detail="The token does not carry an expiry claim.",
            code="invalid_token",
        )
    return datetime.fromtimestamp(int(exp), tz=timezone.utc).replace(tzinfo=None)