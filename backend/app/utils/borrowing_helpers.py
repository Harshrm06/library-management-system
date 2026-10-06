"""Pure helpers for the borrowing rules.

Everything here is a plain function over ``datetime`` values with no database or
model imports, so the rules that decide a due date, a fine and an overdue state
can be unit tested on their own and reused from the controller, a scheduled job
or a script. ``app.models.borrowing_record.BorrowingRecord.is_overdue`` delegates
here so the model and the controller can never disagree about what "overdue"
means.

Timestamps are naive UTC, matching :func:`app.database.utcnow` and the
``DATETIME`` columns they are stored in.

Example:
    >>> calculate_fine(datetime(2026, 1, 1), datetime(2026, 1, 4))
    Decimal('30.00')
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from app.database import utcnow

#: How long a loan runs before the copy is due back. Defined here rather than on
#: the model so the rules can be imported without touching the ORM, which keeps
#: ``app.models.borrowing_record`` free to import :func:`is_overdue` from this
#: module without a circular import.
LOAN_PERIOD_DAYS: int = 14

#: Fine charged per day a copy is late, in whole currency units.
FINE_PER_DAY: Decimal = Decimal("10.00")

#: Money is quantized to this many decimal places.
CENTS: Decimal = Decimal("0.01")


def calculate_due_date(issue_date: datetime) -> datetime:
    """Return the date a copy is due back.

    Args:
        issue_date: When the copy left the library.

    Returns:
        datetime: ``issue_date`` plus the loan period, unchanged in awareness so
        it can be compared with other stored timestamps.

    Raises:
        ValueError: If ``issue_date`` is not a datetime.

    Example:
        >>> calculate_due_date(datetime(2026, 1, 5, 9, 30))
        datetime.datetime(2026, 1, 19, 9, 30)
    """
    if not isinstance(issue_date, datetime):
        raise ValueError("issue_date must be a datetime")
    return issue_date + timedelta(days=LOAN_PERIOD_DAYS)


def calculate_fine(
    due_date: datetime,
    return_date: datetime,
    rate_per_day: int = int(FINE_PER_DAY),
) -> Decimal:
    """Return the fine owed for returning a copy late.

    Only whole days past the due date are charged, and a copy returned on or
    before its due date costs nothing. A partial day still counts once the due
    moment has passed, so ``timedelta.days`` truncation gives "ceil" behaviour
    for a late return and never charges for an early one.

    Args:
        due_date: When the copy was due back.
        return_date: When the copy actually came back.
        rate_per_day: Charge per day late, in whole currency units.

    Returns:
        Decimal: The fine, quantized to two decimal places and never negative.

    Raises:
        ValueError: If either argument is not a datetime, or ``rate_per_day`` is
            negative.

    Example:
        >>> calculate_fine(datetime(2026, 1, 1), datetime(2026, 1, 4))
        Decimal('30.00')
        >>> calculate_fine(datetime(2026, 1, 1), datetime(2025, 12, 31))
        Decimal('0.00')
    """
    if not isinstance(due_date, datetime) or not isinstance(return_date, datetime):
        raise ValueError("due_date and return_date must both be datetimes")
    if rate_per_day < 0:
        raise ValueError("rate_per_day cannot be negative")

    days_late: int = (return_date - due_date).days
    if days_late <= 0:
        return Decimal("0.00").quantize(CENTS)
    fine: Decimal = Decimal(days_late * rate_per_day).quantize(CENTS)
    return fine


def is_overdue(due_date: datetime, return_date: Optional[datetime]) -> bool:
    """Return ``True`` when a copy is late.

    A copy that is still out is compared against now; a copy that has come back
    is compared against its return date, so the answer does not drift once the
    record has been closed.

    Args:
        due_date: When the copy was due back.
        return_date: When it came back, or ``None`` while it is still out.

    Returns:
        bool: ``True`` when the reference moment is past the due date.

    Raises:
        ValueError: If ``due_date`` is not a datetime.

    Example:
        >>> is_overdue(datetime(2026, 1, 1), datetime(2026, 1, 3))
        True
        >>> is_overdue(datetime(2999, 1, 1), None)
        False
    """
    if not isinstance(due_date, datetime):
        raise ValueError("due_date must be a datetime")
    reference: datetime = return_date if return_date is not None else utcnow()
    return reference > due_date


__all__ = [
    "CENTS",
    "FINE_PER_DAY",
    "LOAN_PERIOD_DAYS",
    "calculate_due_date",
    "calculate_fine",
    "is_overdue",
]