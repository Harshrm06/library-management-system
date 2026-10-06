"""Pydantic schemas for the borrowing system.

The module covers the request and response models for the loan endpoints:

* :class:`BorrowingRecordBaseSchema` - the loan fields shared by every payload;
* :class:`BorrowRecordResponse` - a single loan as the API returns it;
* :class:`BorrowingHistoryResponse` - one page of a member's loan history;
* :class:`BorrowRequest` and :class:`ReturnRequest` - the two write payloads;
* :class:`BorrowingHistoryQuery` - pagination and filtering for the history.

Timestamps are validated as a coherent set: a due date cannot precede its issue
date, and a ``RETURNED`` loan must carry the return date that settled it.

Example:
    >>> BorrowRequest(book_id=7).book_id
    7
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

#: Statuses a loan can hold, mirroring ``app.models.borrowing_record.BorrowingStatus``.
VALID_BORROWING_STATUSES: frozenset[str] = frozenset({"BORROWED", "RETURNED", "OVERDUE"})


def _normalize_status(value: str) -> str:
    """Upper-case a status and check it against the known values.

    Args:
        value: The status supplied by the caller.

    Returns:
        str: The uppercase status.

    Raises:
        ValueError: If the status is not one the application supports.
    """
    candidate: str = value.strip().upper()
    if candidate not in VALID_BORROWING_STATUSES:
        raise ValueError(
            f"status must be one of: {', '.join(sorted(VALID_BORROWING_STATUSES))}"
        )
    return candidate


class BorrowingRecordBaseSchema(BaseModel):
    """Loan fields shared by every borrowing payload.

    Intended as the base for administrative payloads. Text statuses are
    normalized to upper case so ``borrowed`` and ``BORROWED`` are the same loan
    state, and the date fields are cross-checked so a record cannot be built
    with an impossible timeline.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: int = Field(
        ge=1, description="Member who borrowed the copy", examples=[1]
    )
    book_id: int = Field(
        ge=1, description="Title that was borrowed", examples=[7]
    )
    issue_date: datetime = Field(
        description="UTC timestamp of when the copy left the library",
        examples=["2026-01-05T09:30:00"],
    )
    due_date: datetime = Field(
        description="UTC timestamp the copy is due back, 14 days after issue",
        examples=["2026-01-19T09:30:00"],
    )
    return_date: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp the copy came back; None while it is out",
        examples=[None],
    )
    status: str = Field(
        default="BORROWED",
        description="One of BORROWED, RETURNED or OVERDUE",
        examples=["BORROWED"],
    )
    fine_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="Outstanding fine, never negative",
        examples=[Decimal("0.00")],
    )

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        """Normalize and check the loan status.

        Args:
            value: The raw status from the caller or the database.

        Returns:
            str: The uppercase status.

        Raises:
            ValueError: If the status is not BORROWED, RETURNED or OVERDUE.
        """
        if not isinstance(value, str):
            raise ValueError("status must be a string")
        return _normalize_status(value)

    @field_validator("fine_amount", mode="before")
    @classmethod
    def _validate_fine_amount(cls, value: object) -> object:
        """Reject a fine the library would never charge.

        Args:
            value: The raw fine, possibly a float or string.

        Returns:
            object: The value unchanged, for Pydantic to coerce.

        Raises:
            ValueError: If the fine is negative.
        """
        if isinstance(value, (int, float, Decimal)) and Decimal(str(value)) < 0:
            raise ValueError("fine_amount cannot be negative")
        return value

    @model_validator(mode="after")
    def _validate_dates(self) -> "BorrowingRecordBaseSchema":
        """Keep the loan timeline coherent.

        Returns:
            BorrowingRecordBaseSchema: The validated payload.

        Raises:
            ValueError: If the due date precedes the issue date, the return date
                precedes the issue date, or the loan is RETURNED with no return
                date.
        """
        if self.due_date < self.issue_date:
            raise ValueError("due_date cannot be earlier than issue_date")
        if self.return_date is not None and self.return_date < self.issue_date:
            raise ValueError("return_date cannot be earlier than issue_date")
        if self.status == "RETURNED" and self.return_date is None:
            raise ValueError("a RETURNED loan must carry return_date")
        return self


class BorrowRecordResponse(BorrowingRecordBaseSchema):
    """A single loan as the API returns it.

    Extends the base with the surrogate key and the row timestamp, and enables
    ``from_attributes`` so the ORM ``BorrowingRecord`` row can be validated
    directly::

        BorrowRecordResponse.model_validate(record_row)

    Example:
        >>> BorrowRecordResponse.model_validate(record_row).status  # doctest: +SKIP
        'BORROWED'
    """

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: int = Field(description="Primary key of the loan record", examples=[1])
    created_at: datetime = Field(
        description="UTC timestamp the loan row was created",
        examples=["2026-01-05T09:30:00"],
    )


class BorrowingHistoryResponse(BaseModel):
    """One page of loan history.

    ``user_id`` identifies whose history this is, and is always present for
    ``GET /api/borrowing-history``. The administrator-wide listing spans every
    member, so it leaves the field ``None`` rather than inventing an id.

    Example:
        >>> BorrowingHistoryResponse(records=[], total=0, user_id=1).records
        []
    """

    model_config = ConfigDict(from_attributes=True)

    records: List[BorrowRecordResponse] = Field(
        default_factory=list, description="Loans on this page"
    )
    total: int = Field(ge=0, description="Total loans matching the query", examples=[4])
    user_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Member the history belongs to; None for a library-wide listing",
        examples=[1],
    )


class BorrowRequest(BaseModel):
    """Payload for ``POST /api/borrow``.

    Only the title is named: the member comes from the bearer token and the
    dates are assigned by the server, so a client cannot forge a due date or
    borrow on someone else's behalf.

    Example:
        >>> BorrowRequest(book_id=7).book_id
        7
    """

    model_config = ConfigDict(extra="forbid")

    book_id: int = Field(
        ge=1, description="Primary key of the title to borrow", examples=[7]
    )


class ReturnRequest(BaseModel):
    """Payload for ``POST /api/return``.

    The loan is named rather than the book, because a member may hold several
    copies of the same title and only one of them comes back at a time.

    Example:
        >>> ReturnRequest(borrowing_record_id=3).borrowing_record_id
        3
    """

    model_config = ConfigDict(extra="forbid")

    borrowing_record_id: int = Field(
        ge=1, description="Primary key of the loan being closed", examples=[3]
    )


class BorrowingHistoryQuery(BaseModel):
    """Query parameters for ``GET /api/borrowing-history``.

    ``skip``/``limit`` describe the window, ``status`` filters exactly, and
    ``start_date``/``end_date`` bound the issue date. The two dates are treated
    as an inclusive range and are rejected when they run backwards.

    Example:
        >>> query = BorrowingHistoryQuery(status="overdue", limit=25)
        >>> query.status, query.limit
        ('OVERDUE', 25)
    """

    model_config = ConfigDict(extra="forbid")

    skip: int = Field(default=0, ge=0, description="Rows to skip, for offset paging")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum rows to return, 1-100"
    )
    status: Optional[str] = Field(
        default=None,
        description="Exact status filter; omit to include every status",
        examples=["OVERDUE"],
    )
    start_date: Optional[datetime] = Field(
        default=None,
        description="Earliest issue date to include, inclusive",
        examples=["2026-01-01T00:00:00"],
    )
    end_date: Optional[datetime] = Field(
        default=None,
        description="Latest issue date to include, inclusive",
        examples=["2026-12-31T23:59:59"],
    )

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> Optional[str]:
        """Normalize an optional status filter.

        Args:
            value: The raw query value; ``None`` or a blank string means no filter.

        Returns:
            str | None: The uppercase status, or ``None`` when absent.

        Raises:
            ValueError: If a status was supplied but is not recognized.
        """
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if not isinstance(value, str):
            raise ValueError("status must be a string")
        return _normalize_status(value)

    @model_validator(mode="after")
    def _validate_date_range(self) -> "BorrowingHistoryQuery":
        """Reject a date range that runs backwards.

        Returns:
            BorrowingHistoryQuery: The validated query.

        Raises:
            ValueError: If ``end_date`` precedes ``start_date``.
        """
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("end_date cannot be earlier than start_date")
        return self