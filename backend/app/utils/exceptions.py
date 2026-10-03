"""Custom application exceptions and FastAPI error handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base class for every error raised by the application."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        """Initialize the exception.

        Args:
            message: Human readable description of the failure.
            code: Optional machine readable error code.
        """
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class BadRequestError(AppException):
    """Raised when the request payload is semantically invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"


class AuthenticationError(AppException):
    """Raised when credentials or a token are missing or invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "authentication_error"


class PermissionDeniedError(AppException):
    """Raised when an authenticated user lacks the required role."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppException):
    """Raised when a resource conflicts with existing data."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers to a FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """Convert an :class:`AppException` into a JSON response."""
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if isinstance(exc, AuthenticationError)
            else None
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a consistent payload for request validation failures."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Request validation failed",
                "code": "validation_error",
                "errors": [
                    {"loc": list(error.get("loc", [])), "msg": error.get("msg", "")}
                    for error in exc.errors()
                ],
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Log unexpected database failures and hide internal details."""
        logger.exception("Database error while handling %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Database error", "code": "database_error"},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Return a generic payload for unhandled exceptions."""
        logger.exception("Unhandled error while handling %s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error", "code": "internal_error"},
        )