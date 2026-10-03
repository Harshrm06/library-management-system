"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers import auth_controller
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.user_schema import TokenResponse, UserCreate, UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new member account",
)
def register(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Create an account and return a JWT for immediate use.

    Args:
        payload: Registration data.
        db: Database session dependency.

    Returns:
        TokenResponse: Access token and the created user.
    """
    user: User = auth_controller.register_user(db, payload)
    return auth_controller.issue_token(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain an access token",
)
def login(
    payload: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange email and password for a JWT.

    Args:
        payload: Login credentials.
        db: Database session dependency.

    Returns:
        TokenResponse: Access token and the authenticated user.
    """
    user: User = auth_controller.authenticate_user(db, payload)
    return auth_controller.issue_token(user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Return the authenticated user profile",
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the profile behind the supplied bearer token.

    Args:
        current_user: The authenticated user resolved by the JWT dependency.

    Returns:
        User: The authenticated user.
    """
    return current_user