"""Authentication endpoints.

The router is mounted at ``/api/auth`` (built from
``settings.api_v1_prefix`` so the mount point stays configurable) and every
error raised by the controller is converted into the ``ErrorResponse``
envelope by the handlers registered in :mod:`app.main`.

Endpoints:
    * ``POST   /api/auth/register``       - create a member account
    * ``POST   /api/auth/login``          - exchange credentials for a JWT
    * ``GET    /api/auth/me``             - read the authenticated profile
    * ``PUT    /api/auth/me``             - update the authenticated profile
    * ``POST   /api/auth/refresh-token``  - mint a new token for the caller
    * ``POST   /api/auth/logout``         - client-side token discard
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config import settings
from app.controllers import auth_controller
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.schemas.user_schema import (
    ErrorResponse,
    LoginSuccessResponse,
    LogoutResponse,
    RegisterSuccessResponse,
    TokenRefreshResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from fastapi import APIRouter, Response

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Add OPTIONS handlers for CORS preflight
@router.options("/register")
@router.options("/login")
@router.options("/me")
@router.options("/refresh-token")
@router.options("/logout")
async def handle_options():
    """Handle CORS preflight requests."""
    return Response(status_code=200)

# Rest of your routes continue below...

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)

ERROR_EXAMPLES: Dict[str, Dict[str, Any]] = {
    "400": {
        "summary": "Bad request",
        "description": "The request could not be understood.",
        "code": "bad_request",
    },
    "401": {
        "summary": "Unauthorized",
        "description": "Provide a bearer token in the Authorization header.",
        "code": "missing_token",
    },
    "403": {
        "summary": "Forbidden",
        "description": "This endpoint requires one of the roles: admin.",
        "code": "insufficient_permissions",
    },
    "404": {
        "summary": "Not found",
        "description": "No user exists with the requested id.",
        "code": "user_not_found",
    },
    "409": {
        "summary": "Conflict",
        "description": "An account already exists for this email address.",
        "code": "email_taken",
    },
    "422": {
        "summary": "Validation failed",
        "description": "One or more fields failed validation.",
        "code": "validation_error",
    },
    "500": {
        "summary": "Server error",
        "description": "An unexpected error occurred while processing the request.",
        "code": "internal_server_error",
    },
}

DEFAULT_ERROR_CODES: tuple[int, ...] = (400, 401, 403, 404, 409, 422, 500)


def error_responses(*codes: int) -> Dict[str, Any]:
    """Build the ``responses=`` mapping for a route.

    Every documented status code references the :class:`ErrorResponse` schema
    and carries a realistic example body, so ``/docs`` shows the exact error
    contract the handlers in :mod:`app.main` emit.

    Args:
        *codes: Status codes worth highlighting for this route; they are added
            to the codes every auth endpoint can return.

    Returns:
        dict: OpenAPI ``responses`` entries keyed by status code.

    Example:
        >>> error_responses(409)["409"]["model"] is ErrorResponse
        True
    """
    responses: Dict[str, Any] = {}
    for code in sorted({*DEFAULT_ERROR_CODES, *codes}):
        example: Dict[str, Any] = ERROR_EXAMPLES[str(code)]
        responses[str(code)] = {
            "model": ErrorResponse,
            "description": f"{code} - {example['summary']}.",
            "content": {
                "application/json": {
                    "examples": {
                        str(code): {
                            "summary": example["summary"],
                            "value": {
                                "success": False,
                                "message": example["summary"],
                                "error": example["description"],
                                "code": example["code"],
                                "timestamp": "2026-01-01T12:00:00+00:00",
                            },
                        }
                    }
                }
            },
        }
    return responses


REGISTER_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "member": {
                        "summary": "Register a member",
                        "value": {
                            "email": "member@example.com",
                            "password": "secretpass1",
                            "first_name": "Ada",
                            "last_name": "Lovelace",
                            "phone": "+1-555-0100",
                            "address": "12 Analytical Way, London",
                        },
                    }
                }
            }
        }
    }
}

LOGIN_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "credentials": {
                        "summary": "Email and password",
                        "value": {"email": "member@example.com", "password": "secretpass1"},
                    }
                }
            }
        }
    }
}

UPDATE_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "partial": {
                        "summary": "Change the phone number only",
                        "value": {"phone": "+1-555-0999"},
                    }
                }
            }
        }
    }
}


@router.post(
    "/register",
    response_model=RegisterSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new member account",
    description=(
        "Creates an account with the `member` role and returns the created "
        "user. Passwords must be at least 6 characters and contain a letter "
        "and a digit. A duplicate email is rejected with 409 Conflict."
    ),
    responses=error_responses(409, 422),
    openapi_extra=REGISTER_REQUEST_EXAMPLE,
)
async def register(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create a member account.

    Args:
        payload: Registration data: email, password, first and last name,
            with optional phone and address.
        db: Database session dependency.

    Returns:
        dict: 201 with `{success, message, data: {user}, timestamp}`.

    Raises:
        ConflictError: If the email is already registered (409).
        ValidationError: If the payload fails validation (422).
    """
    return await auth_controller.register_user(payload, db)


@router.post(
    "/login",
    response_model=LoginSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and obtain an access token",
    description=(
        "Verifies the credentials with bcrypt and returns a signed HS256 JWT "
        "inside a `data` envelope. Unknown emails and wrong passwords return "
        "the same 401 body so accounts cannot be enumerated."
    ),
    responses=error_responses(401, 422),
    openapi_extra=LOGIN_REQUEST_EXAMPLE,
)
async def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Exchange email and password for an access token.

    Args:
        payload: Login credentials.
        db: Database session dependency.

    Returns:
        dict: 200 with `{success, message, data: {token, token_type,
        expires_in, user}, timestamp}`.

    Raises:
        UnauthorizedError: If the credentials are wrong (401).
    """
    return await auth_controller.login_user(payload, db)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Return the authenticated user profile",
    description=(
        "Protected route. Reads the bearer token, then returns the matching "
        "`users` row without the password hash."
    ),
    responses=error_responses(401, 404, 422),
)
async def read_current_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Return the profile behind the supplied bearer token.

    Args:
        current_user: User context resolved by :func:`get_current_user`.
        db: Database session dependency.

    Returns:
        UserResponse: 200 with the authenticated profile.

    Raises:
        UnauthorizedError: If the token is missing, expired or invalid (401).
        NotFoundError: If the account no longer exists (404).
    """
    return await auth_controller.get_user_profile(current_user.id, db)


@router.put(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update the authenticated user profile",
    description=(
        "Protected route. Applies only the fields present in the request; "
        "omitted fields keep their current value. `role` is never accepted."
    ),
    responses=error_responses(401, 404, 422),
    openapi_extra=UPDATE_REQUEST_EXAMPLE,
)
async def update_current_user(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Apply a partial update to the authenticated profile.

    Args:
        payload: Optional `first_name`, `last_name`, `phone` and `address`.
        current_user: User context resolved by :func:`get_current_user`.
        db: Database session dependency.

    Returns:
        UserResponse: 200 with the updated profile.

    Raises:
        UnauthorizedError: If the token is missing, expired or invalid (401).
        NotFoundError: If the account no longer exists (404).
        ValidationError: If the payload fails validation (422).
    """
    return await auth_controller.update_user_profile(current_user.id, payload, db)


@router.post(
    "/refresh-token",
    response_model=TokenRefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue a new access token for the caller",
    description=(
        "Protected route. The API is stateless, so refreshing re-checks the "
        "account and mints a new JWT with the same claims and lifetime."
    ),
    responses=error_responses(401, 404),
)
async def refresh_token(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return a freshly signed token for the authenticated user.

    Args:
        current_user: User context resolved by :func:`get_current_user`.
        db: Database session dependency.

    Returns:
        dict: 200 with `{success, message, token, token_type, expires_in}`.

    Raises:
        UnauthorizedError: If the token is missing, expired, invalid or the
            account is deactivated (401).
        NotFoundError: If the account no longer exists (404).
    """
    return await auth_controller.refresh_user_token(int(current_user["id"]), db)


@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Log the current user out",
    description=(
        "Protected route. Tokens are stateless and are not revoked "
        "server-side; the client must discard its copy. The route exists so "
        "the frontend has a single logout call to make."
    ),
    responses=error_responses(401,),
)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> LogoutResponse:
    """Acknowledge a logout request.

    Args:
        current_user: User context resolved by :func:`get_current_user`.

    Returns:
        LogoutResponse: 200 with `{success: true, message: "Logged out"}`.

    Raises:
        UnauthorizedError: If the token is missing, expired or invalid (401).
    """
    return LogoutResponse(success=True, message="Logged out")