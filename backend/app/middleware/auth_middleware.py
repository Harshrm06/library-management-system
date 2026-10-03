"""JWT verification middleware and authorization dependencies."""

from __future__ import annotations

from typing import Awaitable, Callable, Dict, Iterable, Optional

from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.exceptions import AuthenticationError, PermissionDeniedError
from app.utils.jwt_utils import decode_token

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

PUBLIC_PATHS: tuple[str, ...] = ("/health", "/docs", "/redoc", "/openapi.json")


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str | None:
    """Return a bearer token from the request headers or query string.

    Args:
        request: The incoming request.
        credentials: Credentials parsed by :class:`HTTPBearer`, if present.

    Returns:
        str | None: The raw token when one is available.
    """
    if credentials is not None:
        return credentials.credentials
    header: str | None = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    token_param: str | None = request.query_params.get("token")
    return token_param


class AuthMiddleware(BaseHTTPMiddleware):
    """Attach the decoded JWT payload to ``request.state`` when present.

    The middleware never rejects a request on its own; authorization is
    enforced by :func:`get_current_user` and :func:`require_role` so that
    public endpoints stay reachable. Paths listed in :data:`PUBLIC_PATHS`
    are always skipped.
    """

    def __init__(self, app: ASGIApp, *, public_paths: Iterable[str] = PUBLIC_PATHS) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application being wrapped.
            public_paths: Path prefixes that skip token decoding.
        """
        super().__init__(app)
        self.public_paths: tuple[str, ...] = tuple(public_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Decode the bearer token, when one is supplied, then call the next hop.

        Args:
            request: The incoming request.
            call_next: The next middleware or route handler.

        Returns:
            Response: The response produced by the next hop.
        """
        request.state.user_payload = None
        if not request.url.path.startswith(self.public_paths):
            token: str | None = _extract_token(request, None)
            if token:
                try:
                    request.state.user_payload = decode_token(token)
                except AuthenticationError:
                    request.state.user_payload = None
        return await call_next(request)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the bearer token.

    Args:
        request: The incoming request.
        credentials: Credentials parsed from the ``Authorization`` header.
        db: Database session dependency.

    Returns:
        User: The authenticated, active user.

    Raises:
        AuthenticationError: If the token is missing, invalid or refers to a
            user that no longer exists or has been deactivated.
    """
    token: str | None = _extract_token(request, credentials)
    if not token:
        raise AuthenticationError("Missing authentication token", code="missing_token")

    payload: Dict[str, Any] = decode_token(token)
    subject: str | None = payload.get("sub")
    if subject is None:
        raise AuthenticationError("Invalid authentication token", code="invalid_token")

    try:
        user_id: int = int(subject)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("Invalid authentication token", code="invalid_token") from exc

    user: User | None = db.get(User, user_id)
    if user is None:
        raise AuthenticationError("User not found", code="user_not_found")
    if not user.is_active:
        raise AuthenticationError("User account is inactive", code="inactive_user")

    request.state.user_payload = payload
    return user


def require_role(*roles: UserRole) -> Callable[..., User]:
    """Build a dependency that enforces the given roles.

    Args:
        *roles: Roles allowed to access the endpoint.

    Returns:
        Callable: A FastAPI dependency returning the authenticated user.

    Raises:
        PermissionDeniedError: If the user's role is not in ``roles``.
    """

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        """Validate the role of the authenticated user.

        Args:
            current_user: The authenticated user.

        Returns:
            User: The authenticated user when authorized.
        """
        if roles and current_user.role not in roles:
            raise PermissionDeniedError(
                f"Role '{current_user.role.value}' is not allowed for this resource"
            )
        return current_user

    return dependency