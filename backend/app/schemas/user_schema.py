"""Pydantic schemas for authentication and user management.

The module groups three kinds of models:

* request models - what a client may send (``UserRegisterRequest``,
  ``UserLoginRequest``, ``UserUpdateRequest``);
* response models - what the API returns (``UserResponse``,
  ``LoginSuccessResponse``, ``RegisterSuccessResponse``, ``ErrorResponse``).

Every schema carries ``json_schema_extra`` examples so the interactive
Swagger documentation at ``/docs`` shows realistic payloads.

Example:
    >>> payload = UserRegisterRequest(
    ...     email="member@example.com",
    ...     password="secretpass1",
    ...     first_name="Ada",
    ...     last_name="Lovelace",
    ... )
    >>> payload.role if hasattr(payload, "role") else "member"
    'member'
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.utils.validators import validate_email_format, validate_password_strength, validate_role


def _utcnow() -> datetime:
    """Return the current UTC timestamp used for response envelopes.

    Returns:
        datetime: The current time with timezone information attached.
    """
    return datetime.now(timezone.utc)


class UserBaseSchema(BaseModel):
    """Shared user fields.

    Intended as the base for administrative create/update payloads.
    Registration deliberately does **not** inherit from this class: a client
    must never be able to choose its own role.
    """

    first_name: str = Field(
        min_length=1,
        max_length=100,
        description="Given name of the account holder",
        examples=["Ada"],
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
        description="Family name of the account holder",
        examples=["Lovelace"],
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Optional contact number",
        examples=["+1-555-0100"],
    )
    address: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional postal address",
        examples=["12 Analytical Way, London"],
    )
    role: str = Field(
        default="member",
        description="Account role, either 'admin' or 'member'",
        examples=["member"],
    )

    @field_validator("role")
    @classmethod
    def _validate_role(cls, value: str) -> str:
        """Validate the role against the roles the application supports.

        Args:
            value: The role supplied by the caller.

        Returns:
            str: The normalized, lowercased role.

        Raises:
            ValueError: If the role is neither ``admin`` nor ``member``.
        """
        candidate: str = value.strip().lower()
        if not validate_role(candidate):
            raise ValueError("Role must be either 'admin' or 'member'")
        return candidate


class UserRegisterRequest(BaseModel):
    """Payload for ``POST /api/auth/register``.

    ``role`` is intentionally absent: new accounts are always created as
    ``member`` by the controller.

    Example:
        >>> UserRegisterRequest(
        ...     email="member@example.com",
        ...     password="secretpass1",
        ...     first_name="Ada",
        ...     last_name="Lovelace",
        ... ).email
        'member@example.com'
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        min_length=3,
        max_length=255,
        description="Unique login address, must be a valid email",
        examples=["member@example.com"],
    )
    password: str = Field(
        min_length=6,
        max_length=72,
        description=(
            "At least 6 characters and must contain at least one letter and "
            "one number. bcrypt hashes at most 72 bytes."
        ),
        examples=["secretpass1"],
    )
    first_name: str = Field(
        min_length=1,
        max_length=100,
        description="Given name of the account holder",
        examples=["Ada"],
    )
    last_name: str = Field(
        min_length=1,
        max_length=100,
        description="Family name of the account holder",
        examples=["Lovelace"],
    )
    phone: Optional[str] = Field(
        default=None,
        max_length=20,
        description="Optional contact number",
        examples=["+1-555-0100"],
    )
    address: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional postal address",
        examples=["12 Analytical Way, London"],
    )

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        """Normalize and validate the email address.

        Args:
            value: The email address supplied by the client.

        Returns:
            str: The trimmed, lowercased address.

        Raises:
            ValueError: If the address is not well formed.
        """
        candidate: str = value.strip().lower()
        if not validate_email_format(candidate):
            raise ValueError("Invalid email format")
        return candidate

    @field_validator("password")
    @classmethod
    def _validate_password(cls, value: str) -> str:
        """Validate the password against the strength policy.

        Args:
            value: The plaintext password supplied by the client.

        Returns:
            str: The validated password.

        Raises:
            ValueError: If the password is shorter than 6 characters or lacks
                a letter or a digit.
        """
        is_valid, message = validate_password_strength(value)
        if not is_valid:
            raise ValueError(message)
        return value


class UserLoginRequest(BaseModel):
    """Payload for ``POST /api/auth/login``.

    Example:
        >>> UserLoginRequest(
        ...     email="member@example.com", password="secretpass1"
        ... ).email
        'member@example.com'
    """

    model_config = ConfigDict(extra="forbid")

    email: str = Field(
        min_length=3,
        max_length=255,
        description="Registered login address",
        examples=["member@example.com"],
    )
    password: str = Field(
        min_length=1,
        max_length=72,
        description="Account password",
        examples=["secretpass1"],
    )

    @field_validator("email")
    @classmethod
    def _normalize_email(cls, value: str) -> str:
        """Trim and lowercase the address before matching.

        Args:
            value: The email address supplied by the client.

        Returns:
            str: The trimmed, lowercased address.
        """
        return value.strip().lower()


class UserResponse(BaseModel):
    """Public representation of a user.

    ``model_config`` enables ``from_attributes`` so the ORM ``User`` row can be
    validated directly::

        UserResponse.model_validate(user_row)

    Example:
        >>> UserResponse.model_validate(user_row).role  # doctest: +SKIP
        'member'
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Primary key of the user", examples=[1])
    email: str = Field(description="Login address", examples=["member@example.com"])
    first_name: str = Field(description="Given name", examples=["Ada"])
    last_name: str = Field(description="Family name", examples=["Lovelace"])
    phone: Optional[str] = Field(
        default=None,
        description="Optional contact number, echoed so the client can display it",
        examples=["+1-555-0100"],
    )
    address: Optional[str] = Field(
        default=None,
        description="Optional postal address, echoed so the client can display it",
        examples=["12 Analytical Way, London"],
    )
    role: str = Field(description="'admin' or 'member'", examples=["member"])
    is_active: bool = Field(
        description="Inactive accounts cannot authenticate", examples=[True]
    )
    created_at: datetime = Field(description="UTC creation timestamp")


class LoginData(BaseModel):
    """Payload carried by :class:`LoginSuccessResponse.data`."""

    token: str = Field(
        description="Signed JWT access token (HS256)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(default="bearer", description="Always 'bearer'")
    expires_in: int = Field(
        description="Token lifetime in seconds", examples=[86400]
    )
    user: UserResponse = Field(description="The authenticated user")


class RegisterData(BaseModel):
    """Payload carried by :class:`RegisterSuccessResponse.data`."""

    user: UserResponse = Field(description="The newly created account")


class LoginSuccessResponse(BaseModel):
    """Envelope returned by ``POST /api/auth/login``.

    Example:
        ``LoginData`` requires a token, the profile and the lifetime, so all
        three are spelled out here rather than left to a fixture.

        >>> user = UserResponse(
        ...     id=1, email="member@example.com", first_name="Ada",
        ...     last_name="Lovelace", role="member", is_active=True,
        ...     created_at=datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc),
        ... )
        >>> LoginSuccessResponse(
        ...     message="Login successful",
        ...     data={"token": "a.b.c", "user": user, "expires_in": 3600},
        ... ).success
        True
    """

    success: bool = Field(default=True, description="Always true on success")
    message: str = Field(
        description="Human readable outcome", examples=["Login successful"]
    )
    data: LoginData = Field(description="Access token and user profile")
    timestamp: datetime = Field(
        default_factory=_utcnow, description="Server time of the response"
    )


class RegisterSuccessResponse(BaseModel):
    """Envelope returned by ``POST /api/auth/register``.

    Example:
        >>> user = UserResponse(
        ...     id=1, email="member@example.com", first_name="Ada",
        ...     last_name="Lovelace", role="member", is_active=True,
        ...     created_at=datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc),
        ... )
        >>> RegisterSuccessResponse(
        ...     message="Account created", data={"user": user}
        ... ).data.user.email
        'member@example.com'
    """

    success: bool = Field(default=True, description="Always true on success")
    message: str = Field(
        description="Human readable outcome", examples=["Account created successfully"]
    )
    data: RegisterData = Field(description="The created account")
    timestamp: datetime = Field(
        default_factory=_utcnow, description="Server time of the response"
    )


class TokenRefreshResponse(BaseModel):
    """Envelope returned by ``POST /api/auth/refresh-token``.

    The backend keeps no session state, so refreshing simply issues a new
    token for the still-valid caller.

    Example:
        >>> TokenRefreshResponse(
        ...     message="Token refreshed", token="a.b.c", expires_in=3600
        ... ).success
        True
    """

    success: bool = Field(default=True, description="Always true on success")
    message: str = Field(
        description="Human readable outcome", examples=["Token refreshed"]
    )
    token: str = Field(
        description="Newly issued JWT access token",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(default="bearer", description="Always 'bearer'")
    expires_in: int = Field(
        description="Token lifetime in seconds", examples=[86400]
    )


class LogoutResponse(BaseModel):
    """Envelope returned by ``POST /api/auth/logout``.

    The API is stateless: clients must discard the token themselves.

    Example:
        ``message`` is a required field, so it is supplied here.

        >>> LogoutResponse(message="Logged out").model_dump()["message"]
        'Logged out'
    """

    success: bool = Field(default=True, description="Always true on success")
    message: str = Field(
        description="Human readable outcome", examples=["Logged out"]
    )


class ErrorResponse(BaseModel):
    """Envelope returned for every 4xx and 5xx response.

    Mirrors the JSON body produced by the handlers in
    :func:`app.utils.exceptions.register_exception_handlers`.

    Example:
        ``timestamp`` is generated per response, so the repr is matched with
        ``ELLIPSIS`` rather than compared literally.

        >>> ErrorResponse(  # doctest: +ELLIPSIS
        ...     message="Login failed", error="Incorrect email or password"
        ... )
        ErrorResponse(success=False, message='Login failed', ...)
    """

    success: bool = Field(default=False, description="Always false on failure")
    message: str = Field(
        description="Short summary of the failure",
        examples=["Incorrect email or password"],
    )
    error: str = Field(
        description="Detailed explanation of the failure",
        examples=["The supplied credentials do not match any account."],
    )
    timestamp: datetime = Field(
        default_factory=_utcnow, description="Server time of the response"
    )


class UserUpdateRequest(BaseModel):
    """Payload for ``PUT /api/auth/me``.

    Every field is optional; only the fields present in the request are
    applied by the controller.

    Example:
        >>> UserUpdateRequest(phone="+1-555-0100").model_dump(exclude_unset=True)
        {'phone': '+1-555-0100'}
    """

    model_config = ConfigDict(extra="forbid")

    first_name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="New given name"
    )
    last_name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="New family name"
    )
    phone: Optional[str] = Field(
        default=None, max_length=20, description="New contact number"
    )
    address: Optional[str] = Field(
        default=None, max_length=255, description="New postal address"
    )


from app.models.user import UserRole


class UserRoleUpdate(BaseModel):
    """Payload used by an admin to update a user's role."""

    model_config = ConfigDict(extra="forbid")

    role: UserRole

    @field_validator("role", mode="before")
    @classmethod
    def parse_role(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean in ("admin", "member"):
                return UserRole(v_clean)
        return v


class UserListResponse(BaseModel):
    """Paginated user listing response for admin endpoints."""

    model_config = ConfigDict(from_attributes=True)

    items: list[UserResponse]
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    total: int = Field(description="Total count of matching user records")


UserOut = UserResponse
UserCreate = UserRegisterRequest
UserUpdate = UserUpdateRequest
UserLogin = UserLoginRequest
TokenResponse = LoginSuccessResponse