"""Book ORM model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from app.models.borrowing_record import BorrowingRecord


class Book(Base):
    """A catalog entry with copy-level inventory tracking.

    Attributes:
        id: Surrogate primary key.
        title: Book title.
        author: Book author.
        isbn: Unique 10 or 13 digit identifier used for lookups.
        genre: Optional genre used for catalog filtering.
        description: Optional long form summary. Stored as unbounded ``TEXT``, so the
            column never truncates a synopsis; the limit on how much a client may
            send lives in the request schema, not here.
        total_quantity: Number of copies owned by the library.
        available_quantity: Copies not currently on loan.
        published_year: Optional year of first publication.
        borrowings: Every loan of this title, across all copies.
        created_at: UTC timestamp set when the row is first inserted.
        updated_at: UTC timestamp refreshed on every update.
    """

    __tablename__ = "books"
    __table_args__ = (
        # `isbn` also carries a column level UNIQUE constraint, which MySQL backs
        # with its own index; this one keeps lookups explicit in the metadata.
        Index("ix_books_isbn", "isbn"),
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
        Index("ix_books_genre", "genre"),
        # Inventory can never be negative, and the library cannot lend more
        # copies than it owns. Both rules are enforced by the database as well
        # as by `app.schemas.book_schema`.
        CheckConstraint("total_quantity >= 0", name="ck_books_total_quantity_non_negative"),
        CheckConstraint(
            "available_quantity >= 0", name="ck_books_available_quantity_non_negative"
        ),
        CheckConstraint(
            "available_quantity <= total_quantity",
            name="ck_books_available_within_total",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    isbn: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    genre: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    total_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    borrowings: Mapped[List["BorrowingRecord"]] = relationship(
        "BorrowingRecord", back_populates="book"
    )

    @property
    def borrowing_records(self) -> List["BorrowingRecord"]:
        """Alias returning borrowings relationship."""
        return self.borrowings

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    @property
    def is_available(self) -> bool:
        """Return ``True`` when at least one copy can be borrowed.

        Returns:
            bool: ``True`` if ``available_quantity`` is positive.
        """
        return self.available_quantity > 0

    def __repr__(self) -> str:
        """Return a concise debugging representation of the book.

        Returns:
            str: A string with the primary key, title and available copies.
        """
        return f"<Book id={self.id} title={self.title!r} available={self.available_quantity}>"
