"""User ORM model."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from app.models.borrowing_record import BorrowingRecord


class UserRole(str, enum.Enum):
    """Roles an account can hold."""

    ADMIN = "admin"
    MEMBER = "member"


class User(Base):
    """A library member or an administrator.

    Attributes:
        id: Surrogate primary key.
        email: Unique login address used for authentication.
        password_hash: bcrypt hash of the account password.
        first_name: Given name of the account holder.
        last_name: Family name of the account holder.
        phone: Optional contact number.
        address: Optional postal address.
        role: Either ``admin`` or ``member``; new accounts default to ``member``.
            The enum is stored with its lowercase values, so the MySQL column
            holds exactly ``'admin'`` / ``'member'``.
        is_active: Inactive accounts are rejected by the auth dependency.
        borrowings: Every loan this account has taken, newest last.
        created_at: UTC timestamp set when the row is first inserted.
        updated_at: UTC timestamp refreshed on every update.
    """

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_role", "role"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        default=UserRole.MEMBER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    borrowings: Mapped[List["BorrowingRecord"]] = relationship(
        "BorrowingRecord", back_populates="user"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        """Return a concise debugging representation of the user.

        Returns:
            str: A string with the primary key, email and role.
        """
        return f"<User id={self.id} email={self.email!r} role={self.role}>"