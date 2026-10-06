"""Custom application exceptions and FastAPI error handlers.

Every exception carries an HTTP ``status_code``, a short ``message`` and a
longer ``detail`` so that controllers can raise a typed error and the API
always answers with the ``ErrorResponse`` envelope documented in
``app.schemas.user_schema``::

    {"success": false, "message": "...", "error": "...", "code": "conflict", "timestamp": "..."}
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def _utcnow() -> str:
    """Return the current UTC timestamp as an ISO 8601 string.

    Returns:
        str: The current UTC time, e.g. ``2026-01-01T12:00:00+00:00``.
    """
    return datetime.now(timezone.utc).isoformat()


class AppException(Exception):
    """Base class for every error raised by the application."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        detail: str | None = None,
        code: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            message: Short human readable summary, e.g. ``"Email already exists"``.
            detail: Optional longer explanation; defaults to ``message``.
            code: Optional machine readable error code.
            status_code: Optional HTTP status override for this instance.
        """
        super().__init__(message)
        self.message: str = message
        self.detail: str = detail if detail is not None else message
        self.code: str = code if code is not None else type(self).code
        if status_code is not None:
            self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the exception as an ``ErrorResponse`` style body.

        Returns:
            dict: ``success=False`` plus the message, detail, code and the
            server timestamp.
        """
        return {
            "success": False,
            "message": self.message,
            "error": self.detail,
            "code": self.code,
            "timestamp": _utcnow(),
        }


class ValidationError(AppException):
    """Raised when request data fails validation (HTTP 422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"


class BadRequestError(AppException):
    """Raised when a request is semantically invalid (HTTP 400)."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"


class UnauthorizedError(AppException):
    """Raised when a caller is missing or has invalid credentials (HTTP 401)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ForbiddenError(AppException):
    """Raised when an authenticated caller lacks permission (HTTP 403)."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


class NotFoundError(AppException):
    """Raised when a requested resource does not exist (HTTP 404)."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppException):
    """Raised when a resource conflicts with existing data (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class InternalServerError(AppException):
    """Raised for unexpected failures that must not leak internals (HTTP 500)."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "internal_server_error"


# Backwards compatible aliases used by earlier imports.
AuthenticationError = UnauthorizedError
PermissionDeniedError = ForbiddenError


def register_exception_handlers(app: FastAPI) -> None:
    """Attach JSON error handlers to a FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
        """Convert an :class:`AppException` into a JSON response.

        Args:
            request: The incoming request.
            exc: The raised application exception.

        Returns:
            JSONResponse: The error response, with a ``WWW-Authenticate``
            header for unauthorized failures.
        """
        headers = (
            {"WWW-Authenticate": "Bearer"}
            if exc.status_code == status.HTTP_401_UNAUTHORIZED
            else None
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return a consistent payload for request validation failures.

        Args:
            request: The incoming request.
            exc: The validation error raised by FastAPI.

        Returns:
            JSONResponse: A 422 response listing the offending fields.
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": "Request validation failed",
                "error": "One or more fields failed validation.",
                "code": "validation_error",
                "timestamp": _utcnow(),
                "errors": [
                    {"loc": list(error.get("loc", [])), "msg": error.get("msg", "")}
                    for error in exc.errors()
                ],
            },
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Log unexpected database failures and hide internal details.

        Args:
            request: The incoming request.
            exc: The database error.

        Returns:
            JSONResponse: A 500 response with a generic message.
        """
        logger.exception("Database error while handling %s", request.url.path)
        error = InternalServerError(
            "Database error",
            detail="The request could not be completed because of a database error.",
            code="database_error",
        )
        return JSONResponse(status_code=error.status_code, content=error.to_dict())

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Return a generic payload for unhandled exceptions.

        Args:
            request: The incoming request.
            exc: The unhandled exception.

        Returns:
            JSONResponse: A 500 response with a generic message.
        """
        logger.exception("Unhandled error while handling %s", request.url.path)
        error = InternalServerError(
            "Internal server error",
            detail="An unexpected error occurred while processing the request.",
        )
        return JSONResponse(status_code=error.status_code, content=error.to_dict())