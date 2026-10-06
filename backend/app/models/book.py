"""Book ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.borrowing_record import BorrowingRecord


class Book(Base):
    """A book in the library catalog with inventory tracking."""

    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    author: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    borrowing_records: Mapped[list[BorrowingRecord]] = relationship(
        "BorrowingRecord", back_populates="book", cascade="all, delete-orphan"
    )

    @property
    def is_available(self) -> bool:
        """Return ``True`` when at least one copy can be borrowed."""
        return self.available_quantity > 0

    def __repr__(self) -> str:
        """Return a debugging representation of the book."""
        return f"<Book id={self.id} title={self.title!r} available={self.available_quantity}>"