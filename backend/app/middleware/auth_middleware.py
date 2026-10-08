"""JWT authentication middleware and authorization dependencies."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional

from fastapi import Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.database import get_db
from app.models.user import User, UserRole
from app.utils.exceptions import NotFoundError, PermissionDeniedError, UnauthorizedError
from app.utils.jwt_utils import verify_token

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

PUBLIC_PATHS: tuple[str, ...] = ("/health", "/docs", "/redoc", "/openapi.json")

ROLE_ADMIN: str = UserRole.ADMIN.value
ROLE_MEMBER: str = UserRole.MEMBER.value


def extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """Return the bearer token carried by a request."""
    if credentials is not None:
        return credentials.credentials
    if request is None:
        return None
    header: Optional[str] = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return request.query_params.get("token")


def _user_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a decoded token payload into the request user context."""
    user_id: Any = payload.get("user_id", payload.get("sub"))
    if user_id is None:
        raise UnauthorizedError(
            "Invalid authentication token",
            detail="The token does not identify a user.",
            code="invalid_token",
        )
    role: Any = payload.get("role", ROLE_MEMBER)
    return {
        "id": user_id,
        "user_id": user_id,
        "email": payload.get("email"),
        "role": role.value if hasattr(role, "value") else role,
        "token": payload,
    }


class AuthMiddleware(BaseHTTPMiddleware):
    """Attach the decoded JWT payload to request.state when present."""

    def __init__(self, app: ASGIApp, *, public_paths: Iterable[str] = PUBLIC_PATHS) -> None:
        super().__init__(app)
        self.public_paths: tuple[str, ...] = tuple(public_paths)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Decode the bearer token and pass preflight requests through untouched."""
        if request.method == "OPTIONS":
            return await call_next(request)

        request.state.user_payload = None
        if not request.url.path.startswith(self.public_paths):
            token: Optional[str] = extract_token(request)
            if token:
                try:
                    request.state.user_payload = verify_token(token)
                except UnauthorizedError:
                    request.state.user_payload = None
        return await call_next(request)


def verify_jwt_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """Verify the bearer token and return the authenticated user payload dict."""
    token: Optional[str] = extract_token(request, credentials)
    if not token:
        raise UnauthorizedError(
            "Missing authentication token",
            detail="Provide a bearer token in the Authorization header.",
            code="missing_token",
        )
    payload: Dict[str, Any] = verify_token(token)
    request.state.user_payload = payload
    return _user_context(payload)


def get_current_user(
    current_user_data: Dict[str, Any] = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
) -> User:
    """Return the authenticated User ORM record for protected routes."""
    user_id = current_user_data.get("id") or current_user_data.get("user_id")
    user: Optional[User] = db.get(User, int(user_id)) if user_id is not None else None
    if user is None:
        raise NotFoundError("User not found", code="user_not_found")
    if not user.is_active:
        raise UnauthorizedError("User account is inactive", code="inactive_user")
    return user


def load_current_user_record(
    current_user_data: Dict[str, Any] = Depends(verify_jwt_token),
    db: Session = Depends(get_db),
) -> User:
    """Load the ORM row for the authenticated user."""
    return get_current_user(current_user_data, db)


def require_role(*roles: Any) -> Callable[..., User]:
    """Build a dependency that enforces one of roles and returns the User ORM object."""
    allowed_roles = {r.value if hasattr(r, "value") else str(r).lower() for r in roles}

    def dependency(
        user: User = Depends(get_current_user),
    ) -> User:
        user_role_str = user.role.value.lower() if hasattr(user.role, "value") else str(user.role).lower()
        if allowed_roles and user_role_str not in allowed_roles:
            raise PermissionDeniedError(
                "Insufficient permissions for this resource",
                code="permission_denied",
            )
        return user

    return dependency


def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Allow only administrators."""
    user_role_str = user.role.value.lower() if hasattr(user.role, "value") else str(user.role).lower()
    if user_role_str != ROLE_ADMIN.lower():
        raise PermissionDeniedError(
            "Administrator access required",
            code="permission_denied",
        )
    return user


def require_member(
    user: User = Depends(get_current_user),
) -> User:
    """Allow only library members."""
    user_role_str = user.role.value.lower() if hasattr(user.role, "value") else str(user.role).lower()
    if user_role_str != ROLE_MEMBER.lower():
        raise PermissionDeniedError(
            "Member access required",
            code="permission_denied",
        )
    return user