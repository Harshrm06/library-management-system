"""Request and response schemas for user authentication and admin user management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user import UserRole

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserBase(BaseModel):
    """Fields shared by every user payload."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    """Payload used to register a new account."""

    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=72)


class UserLogin(BaseModel):
    """Payload used to authenticate an account."""

    email: str = Field(min_length=3, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=72)


class UserUpdate(UserBase):
    """Payload used to update the authenticated user's profile."""

    model_config = ConfigDict(extra="forbid")

    email: str | None = Field(default=None, min_length=3, max_length=255, pattern=EMAIL_PATTERN)
    password: str | None = Field(default=None, min_length=8, max_length=72)


class UserOut(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None = None
    address: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """JWT issued after a successful registration or login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token lifetime in seconds")
    user: UserOut


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

    items: List[UserOut]
    page: int = Field(default=1, ge=1, description="Current page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")
    total: int = Field(description="Total count of matching user records")