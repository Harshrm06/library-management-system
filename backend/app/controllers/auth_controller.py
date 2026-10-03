"""Authentication business logic."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User, UserRole
from app.schemas.user_schema import TokenResponse, UserCreate, UserLogin, UserOut
from app.utils.bcrypt_utils import hash_password, verify_password
from app.utils.exceptions import AuthenticationError, ConflictError
from app.utils.jwt_utils import create_access_token


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Look up a user by email address.

    Args:
        db: Database session.
        email: Email address to search for, matched case-insensitively.

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


def register_user(db: Session, payload: UserCreate) -> User:
    """Create a new member account.

    Args:
        db: Database session.
        payload: Validated registration data.

    Returns:
        User: The persisted user.

    Raises:
        ConflictError: If the email address is already registered.
    """
    email: str = payload.email.strip().lower()
    if get_user_by_email(db, email) is not None:
        raise ConflictError("Email is already registered")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone=payload.phone,
        address=payload.address,
        role=UserRole.MEMBER,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Email is already registered") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: UserLogin) -> User:
    """Validate credentials and return the matching user.

    Args:
        db: Database session.
        payload: Validated login data.

    Returns:
        User: The authenticated user.

    Raises:
        AuthenticationError: If the credentials are invalid or the account is
            inactive.
    """
    user: User | None = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthenticationError("Incorrect email or password", code="invalid_credentials")
    if not user.is_active:
        raise AuthenticationError("User account is inactive", code="inactive_user")
    return user


def issue_token(user: User) -> TokenResponse:
    """Build the login/registration response for a user.

    Args:
        user: The authenticated user.

    Returns:
        TokenResponse: Access token plus public user data.
    """
    token: str = create_access_token(user.id, role=user.role.value)
    return TokenResponse(
        access_token=token,
        expires_in=settings.jwt_expiry_seconds,
        user=UserOut.model_validate(user),
    )