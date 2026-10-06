"""Authentication business logic.

The public functions are ``async`` so they compose with the rest of the
async API, while every database interaction is delegated to
:func:`asyncio.to_thread`. The SQLAlchemy ``Session`` is a blocking object and
a Session is not safe to share across threads, so each call runs to
completion inside a single worker thread instead of blocking the event loop.

Responsibilities:

* register an account (always with the ``member`` role),
* authenticate credentials and issue a JWT,
* read and update a user profile.

Security notes:

* passwords are hashed with bcrypt and never returned or logged,
* login compares against a dummy hash when the email is unknown so the
  response time does not reveal whether an account exists,
* every commit is wrapped so a failed write can never leave a session dirty.
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from datetime import datetime, timezone
from functools import cache
from typing import Any, Callable, Dict, Optional, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserRole
from app.schemas.user_schema import (
    LoginSuccessResponse,
    RegisterSuccessResponse,
    TokenRefreshResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.utils.bcrypt_utils import hash_password, verify_password
from app.utils.exceptions import (
    ConflictError,
    InternalServerError,
    NotFoundError,
    UnauthorizedError,
)
from app.utils.jwt_utils import create_access_token

logger = logging.getLogger(__name__)

T = TypeVar("T")


@cache
def _dummy_hash() -> str:
    """Return a throwaway bcrypt hash used to equalize login timing.

    Returns:
        str: A valid bcrypt hash of a random string, computed once per process.
    """
    return hash_password(secrets.token_urlsafe(32))


def _utcnow() -> datetime:
    """Return the current UTC timestamp used in response payloads.

    Returns:
        datetime: The current UTC time with timezone information attached.
    """
    return datetime.now(timezone.utc)


async def _to_thread(function: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run a blocking callable in a worker thread.

    Args:
        function: The blocking callable, typically a SQLAlchemy operation.
        *args: Positional arguments forwarded to ``function``.
        **kwargs: Keyword arguments forwarded to ``function``.

    Returns:
        The value returned by ``function``.
    """
    return await asyncio.to_thread(function, *args, **kwargs)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Look up a user by email address, case-insensitively.

    Args:
        db: Database session.
        email: Email address to search for.

    Returns:
        User | None: The matching user, or ``None`` when absent.
    """
    normalized: str = email.strip().lower()
    statement = select(User).where(func.lower(User.email) == normalized)
    return db.execute(statement).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Look up a user by primary key.

    Args:
        db: Database session.
        user_id: Primary key of the user.

    Returns:
        User | None: The matching user, or ``None`` when absent.
    """
    return db.get(User, user_id)


def _register_user(request: UserRegisterRequest, db: Session) -> Dict[str, Any]:
    """Create a member account. See :func:`register_user` for details."""
    email: str = request.email.strip().lower()
    if get_user_by_email(db, email) is not None:
        logger.warning("Registration rejected: email already registered")
        raise ConflictError(
            "Email is already registered",
            detail="An account already exists for this email address.",
            code="email_taken",
        )

    user = User(
        email=email,
        password_hash=hash_password(request.password),
        first_name=request.first_name.strip(),
        last_name=request.last_name.strip(),
        phone=request.phone,
        address=request.address,
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Registration rejected: unique constraint violation")
        raise ConflictError(
            "Email is already registered",
            detail="An account already exists for this email address.",
            code="email_taken",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Registration failed for %s", email)
        raise InternalServerError(
            "Could not create the account",
            detail="The account could not be saved. Please try again later.",
            code="registration_failed",
        ) from exc
    db.refresh(user)
    logger.info("Registered member %s (id=%s)", user.email, user.id)
    return RegisterSuccessResponse(
        message="Account created successfully",
        data={"user": UserResponse.model_validate(user)},
    ).model_dump()


def _login_user(request: UserLoginRequest, db: Session) -> Dict[str, Any]:
    """Authenticate credentials. See :func:`login_user` for details."""
    user: Optional[User] = get_user_by_email(db, request.email)
    if user is None:
        verify_password(request.password, _dummy_hash())
        logger.warning("Login rejected: unknown email")
        raise UnauthorizedError(
            "Incorrect email or password",
            detail="The supplied credentials do not match any account.",
            code="invalid_credentials",
        )
    if not verify_password(request.password, user.password_hash):
        logger.warning("Login rejected: wrong password for %s", user.email)
        raise UnauthorizedError(
            "Incorrect email or password",
            detail="The supplied credentials do not match any account.",
            code="invalid_credentials",
        )
    if not user.is_active:
        logger.warning("Login rejected: inactive account %s", user.email)
        raise UnauthorizedError(
            "User account is inactive",
            detail="This account has been deactivated. Contact an administrator.",
            code="inactive_user",
        )

    token: str = create_access_token(
        {"user_id": user.id, "email": user.email, "role": user.role.value}
    )
    logger.info("Login succeeded for %s (id=%s)", user.email, user.id)
    return LoginSuccessResponse(
        message="Login successful",
        data={
            "token": token,
            "token_type": "bearer",
            "expires_in": settings.jwt_expiry_seconds,
            "user": UserResponse.model_validate(user),
        },
    ).model_dump()


def _get_user_profile(user_id: int, db: Session) -> UserResponse:
    """Read a profile. See :func:`get_user_profile` for details."""
    user: Optional[User] = get_user_by_id(db, user_id)
    if user is None:
        logger.warning("Profile lookup failed: user %s not found", user_id)
        raise NotFoundError(
            "User not found",
            detail=f"No user exists with id {user_id}.",
            code="user_not_found",
        )
    if not user.is_active:
        logger.warning("Profile lookup failed: user %s is inactive", user_id)
        raise UnauthorizedError(
            "User account is inactive",
            detail="This account has been deactivated. Contact an administrator.",
            code="inactive_user",
        )
    return UserResponse.model_validate(user)


def _update_user_profile(
    user_id: int, request: UserUpdateRequest, db: Session
) -> UserResponse:
    """Update a profile. See :func:`update_user_profile` for details."""
    user: Optional[User] = get_user_by_id(db, user_id)
    if user is None:
        logger.warning("Profile update failed: user %s not found", user_id)
        raise NotFoundError(
            "User not found",
            detail=f"No user exists with id {user_id}.",
            code="user_not_found",
        )
    if not user.is_active:
        logger.warning("Profile update failed: user %s is inactive", user_id)
        raise UnauthorizedError(
            "User account is inactive",
            detail="This account has been deactivated. Contact an administrator.",
            code="inactive_user",
        )

    changes: Dict[str, Any] = request.model_dump(exclude_unset=True)
    changes.pop("role", None)
    for field, value in changes.items():
        setattr(user, field, value.strip() if isinstance(value, str) else value)

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Profile update failed for user %s", user_id)
        raise InternalServerError(
            "Could not update the profile",
            detail="The profile could not be saved. Please try again later.",
            code="update_failed",
        ) from exc
    db.refresh(user)
    logger.info("Updated profile for user %s (%s changed)", user_id, len(changes))
    return UserResponse.model_validate(user)


async def register_user(request: UserRegisterRequest, db: Session) -> Dict[str, Any]:
    """Register a new member account.

    Args:
        request: Validated registration data. The email format is checked by
            the schema, and the account is always created with the ``member``
            role.
        db: Database session.

    Returns:
        dict: The ``RegisterSuccessResponse`` envelope with the created user;
        the password hash is never included.

    Raises:
        ConflictError: If the email address is already registered (HTTP 409).
        InternalServerError: If the insert fails for any other reason.

    Example:
        >>> await register_user(  # doctest: +SKIP
        ...     UserRegisterRequest(
        ...         email="member@example.com",
        ...         password="secretpass1",
        ...         first_name="Ada",
        ...         last_name="Lovelace",
        ...     ),
        ...     db,
        ... )
    """
    return await _to_thread(_register_user, request, db)


async def login_user(request: UserLoginRequest, db: Session) -> Dict[str, Any]:
    """Authenticate credentials and issue a JWT.

    Args:
        request: Validated login data.
        db: Database session.

    Returns:
        dict: The ``LoginSuccessResponse`` envelope containing the token, its
        lifetime in seconds and the user profile.

    Raises:
        UnauthorizedError: If the credentials are wrong (HTTP 401) or the
            account is inactive.

    Example:
        >>> await login_user(  # doctest: +SKIP
        ...     UserLoginRequest(email="member@example.com", password="secretpass1"),
        ...     db,
        ... )
    """
    return await _to_thread(_login_user, request, db)


async def get_user_profile(user_id: int, db: Session) -> UserResponse:
    """Return a user profile.

    Args:
        user_id: Primary key of the user to read.
        db: Database session.

    Returns:
        UserResponse: The public profile of the user.

    Raises:
        NotFoundError: If no user has that id (HTTP 404).
        UnauthorizedError: If the account has been deactivated (HTTP 401).
    """
    return await _to_thread(_get_user_profile, user_id, db)


async def update_user_profile(
    user_id: int, request: UserUpdateRequest, db: Session
) -> UserResponse:
    """Update the editable fields of a user profile.

    Only the fields present in the request are applied, so omitted values keep
    their current content. ``role`` is never accepted from the client.

    Args:
        user_id: Primary key of the user to update.
        request: Validated partial update.
        db: Database session.

    Returns:
        UserResponse: The updated profile.

    Raises:
        NotFoundError: If no user has that id (HTTP 404).
        UnauthorizedError: If the account has been deactivated (HTTP 401).
        InternalServerError: If the commit fails (HTTP 500).
    """
    return await _to_thread(_update_user_profile, user_id, request, db)


def _refresh_token(user_id: int, db: Session) -> Dict[str, Any]:
    """Issue a fresh token. See :func:`refresh_user_token` for details."""
    user: Optional[User] = get_user_by_id(db, user_id)
    if user is None:
        logger.warning("Token refresh failed: user %s not found", user_id)
        raise NotFoundError(
            "User not found",
            detail=f"No user exists with id {user_id}.",
            code="user_not_found",
        )
    if not user.is_active:
        logger.warning("Token refresh failed: user %s is inactive", user_id)
        raise UnauthorizedError(
            "User account is inactive",
            detail="This account has been deactivated. Contact an administrator.",
            code="inactive_user",
        )
    token: str = create_access_token(
        {"user_id": user.id, "email": user.email, "role": user.role.value}
    )
    logger.info("Refreshed token for %s (id=%s)", user.email, user.id)
    return TokenRefreshResponse(
        message="Token refreshed",
        token=token,
        expires_in=settings.jwt_expiry_seconds,
    ).model_dump()


async def refresh_user_token(user_id: int, db: Session) -> Dict[str, Any]:
    """Issue a new access token for an already authenticated user.

    The API holds no session store, so a refresh re-validates the user record
    and mints a new JWT with the same claims and lifetime.

    Args:
        user_id: Primary key of the authenticated user.
        db: Database session.

    Returns:
        dict: The ``TokenRefreshResponse`` envelope with the new token.

    Raises:
        NotFoundError: If the account no longer exists (HTTP 404).
        UnauthorizedError: If the account has been deactivated (HTTP 401).
    """
    return await _to_thread(_refresh_token, user_id, db)