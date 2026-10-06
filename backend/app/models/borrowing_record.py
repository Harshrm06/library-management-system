"""Borrowing record ORM model."""

from __future__ import annotations

import enum
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, Numeric, event
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship

from app.database import Base, utcnow
from app.utils.borrowing_helpers import (
    LOAN_PERIOD_DAYS,
    is_overdue as helpers_is_overdue,
)

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from app.models.book import Book
    from app.models.user import User


class BorrowingStatus(str, enum.Enum):
    """Lifecycle states a borrowing record moves through."""

    BORROWED = "BORROWED"
    RETURNED = "RETURNED"
    OVERDUE = "OVERDUE"


def _default_due_date() -> datetime:
    """Return a fallback due date for a row inserted without one.

    Normally :func:`_set_due_date` derives the due date from the row's own
    ``issue_date``, so the loan period is exact. This fallback only applies when
    a row reaches the database without going through the ORM, where the two
    timestamps cannot be derived from each other.

    Returns:
        datetime: The current UTC time plus the loan period, without a tzinfo.
    """
    return utcnow() + timedelta(days=LOAN_PERIOD_DAYS)


class BorrowingRecord(Base):
    """One loan of one copy of a book to one member.

    The row is the audit trail for a physical copy: it is written when the copy
    leaves the library and completed when it comes back, so ``return_date`` and
    ``fine_amount`` are the only fields that change afterwards.

    Attributes:
        id: Surrogate primary key.
        user_id: Member who borrowed the copy; references ``users.id``.
        book_id: Title that was borrowed; references ``books.id``. The copy count
            lives on the book, not here, so several records may share a ``book_id``.
        issue_date: UTC timestamp of when the copy left the library.
        due_date: UTC timestamp the copy is due back, 14 days after issue.
        return_date: UTC timestamp the copy came back, or ``None`` while it is out.
        status: Either ``BORROWED``, ``RETURNED`` or ``OVERDUE``; new records start
            as ``BORROWED``. The enum is stored with its uppercase values.
        fine_amount: Outstanding fine in the library's currency, never negative.
        created_at: UTC timestamp set when the row is first inserted.
        updated_at: UTC timestamp refreshed on every update.
    """

    __tablename__ = "borrowing_records"
    __table_args__ = (
        # History is always read per member ("what has this person borrowed?")
        # and per title ("which copies are still out?"), so both foreign keys are
        # indexed. The status index serves the overdue sweep and status filters.
        Index("ix_borrowing_user_id", "user_id"),
        Index("ix_borrowing_book_id", "book_id"),
        Index("ix_borrowing_status", "status"),
        # A due date before the issue date is meaningless, and a library never
        # charges a negative fine. Both rules are enforced by the database as
        # well as by `app.schemas.borrowing_record_schema`.
        CheckConstraint("due_date >= issue_date", name="ck_borrowing_due_after_issue"),
        CheckConstraint("fine_amount >= 0", name="ck_borrowing_fine_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey("books.id"), nullable=False)
    issue_date: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    due_date: Mapped[datetime] = mapped_column(
        DateTime, default=_default_due_date, nullable=False
    )
    return_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[BorrowingStatus] = mapped_column(
        Enum(
            BorrowingStatus,
            name="borrowing_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            # Without this, SQLAlchemy defaults to `create_constraint=False` and a
            # backend with no native enum - SQLite - emits a bare
            # `status VARCHAR(8) NOT NULL` that accepts any text. MySQL and
            # PostgreSQL get a real enum type either way, so the constraint is
            # what makes SQLite behave like them: the database itself then
            # rejects a status outside the enum, which is the last line of
            # defence for a raw SQL write or a future migration.
            create_constraint=True,
        ),
        default=BorrowingStatus.BORROWED,
        nullable=False,
    )
    fine_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="borrowings")
    book: Mapped["Book"] = relationship("Book", back_populates="borrowings")

    def is_overdue(self) -> bool:
        """Return ``True`` when the copy is late.

        A record counts as overdue when its status is already ``OVERDUE``, or
        while it is still ``BORROWED`` and the reference moment - the return date
        if the copy came back, otherwise now - is past the due date. A ``RETURNED``
        record is never overdue; lateness on a completed loan belongs in
        ``fine_amount``, and the status has been settled.

        The date comparison itself lives in
        :func:`app.utils.borrowing_helpers.is_overdue`, so the controller and this
        method can never disagree.

        Returns:
            bool: ``True`` when the copy is late.

        Note:
            Column defaults are applied by the database on flush, so a row that
            has never been inserted still reads ``status is None``. ``None`` is
            treated as ``BORROWED`` here, which is the column default, so an
            unflushed record still reports correctly.

        Example:
            A loan due in January 2010 is late today, whatever the status says.
            The row is built in memory, so the example needs the full model
            package imported before the relationships resolve::

            >>> past = BorrowingRecord(  # doctest: +SKIP
            ...     user_id=1,
            ...     book_id=1,
            ...     issue_date=datetime(2010, 1, 1),
            ...     due_date=datetime(2010, 1, 15),
            ... )
            >>> past.is_overdue()  # doctest: +SKIP
            True
        """
        if self.status == BorrowingStatus.OVERDUE:
            return True
        if self.status is not None and self.status != BorrowingStatus.BORROWED:
            return False
        return helpers_is_overdue(self.due_date, self.return_date)

    def __repr__(self) -> str:
        """Return a concise debugging representation of the record.

        Returns:
            str: A string with the primary key, member, book and status.
        """
        return (
            f"<BorrowingRecord id={self.id} user_id={self.user_id} "
            f"book_id={self.book_id} status={self.status}>"
        )


@event.listens_for(BorrowingRecord, "before_insert")
def _set_due_date(_mapper: Mapper[Any], _connection: Connection, target: BorrowingRecord) -> None:
    """Derive ``due_date`` from the row's own ``issue_date`` on insert.

    Both timestamps have independent column defaults, so letting each call
    ``utcnow()`` on its own leaves the due date a few microseconds off the issue
    date plus the loan period. Filling them in here, after the caller has had a
    chance to supply either one, keeps ``due_date`` exactly
    :data:`LOAN_PERIOD_DAYS` after ``issue_date``.

    An explicitly supplied ``due_date`` is always respected, so a shortened or
    extended loan period still works.

    Args:
        _mapper: The mapper firing the event; unused.
        _connection: The connection being used; unused.
        target: The row about to be inserted.
    """
    if target.issue_date is None:
        target.issue_date = utcnow()
    if target.due_date is None:
        target.due_date = target.issue_date + timedelta(days=LOAN_PERIOD_DAYS)