"""BorrowingRecord ORM model."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.book import Book
    from app.models.user import User


class BorrowingStatus(str, enum.Enum):
    """Status options for a borrowing record."""

    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


class BorrowingRecord(Base):
    """A borrowing transaction tracking book issue, due date, return and fines."""

    __tablename__ = "borrowing_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    return_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[BorrowingStatus] = mapped_column(
        SQLEnum(BorrowingStatus, name="borrowing_status"),
        default=BorrowingStatus.BORROWED,
        nullable=False,
        index=True,
    )
    fine_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship("User", back_populates="borrowing_records")
    book: Mapped[Book] = relationship("Book", back_populates="borrowing_records")

    def __repr__(self) -> str:
        """Return a debugging representation of the borrowing record."""
        return (
            f"<BorrowingRecord id={self.id} user_id={self.user_id} "
            f"book_id={self.book_id} status={self.status.value!r}>"
        )
