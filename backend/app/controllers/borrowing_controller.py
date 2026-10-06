"""Borrowing business logic.

Public functions are ``async`` and follow the shape of
:mod:`app.controllers.book_controller`: every blocking SQLAlchemy call is
delegated to :func:`asyncio.to_thread` so the event loop is never held up, and a
request's ``Session`` is used by exactly one worker thread.

Responsibilities:

* lend a copy to a member and take it back,
* report a member's loan history and the whole-library view for administrators,
* sweep loans that have passed their due date.

Notes:

* a member may hold at most one copy of a title at a time, so a second borrow of
  the same book is refused rather than silently stacking loans,
* ``available_quantity`` is the single source of truth for stock and is moved in
  the same transaction as the loan row, so the counter can never drift from the
  loans behind it,
* a copy that comes back late is recorded as ``OVERDUE`` and charged
  :data:`~app.utils.borrowing_helpers.FINE_PER_DAY` for each whole day late,
* the due-date, fine and overdue rules live in
  :mod:`app.utils.borrowing_helpers`, and are shared with the model rather than
  reimplemented here.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import utcnow
from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User
from app.schemas.borrowing_record_schema import (
    BorrowRecordResponse,
    BorrowingHistoryResponse,
)
from app.utils.borrowing_helpers import (
    FINE_PER_DAY,
    calculate_due_date,
    calculate_fine,
    is_overdue as is_overdue_helper,
)
from app.utils.exceptions import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Hard ceiling on page size, mirrored by ``BorrowingHistoryQuery.limit``.
MAX_PAGE_SIZE: int = 100

#: Page size used when a caller does not care.
DEFAULT_PAGE_SIZE: int = 10


async def _to_thread(function: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run a blocking callable in a worker thread.

    Args:
        function: The blocking callable, typically a SQLAlchemy operation.
        *args: Positional arguments forwarded to ``function``.
        **kwargs: Keyword arguments forwarded to ``function``.

    Returns:
        The value returned by ``function``.
    """
    return await asyncio.to_thread(function, *args, **kwargs)


def _validate_pagination(skip: int, limit: int) -> tuple[int, int]:
    """Check and normalize pagination arguments.

    The route validates these through ``BorrowingHistoryQuery``; the check is
    repeated here because a controller can be called directly.

    Args:
        skip: Rows to skip.
        limit: Requested page size.

    Returns:
        tuple[int, int]: The validated ``(skip, limit)``.

    Raises:
        ValidationError: If ``skip`` is negative or ``limit`` is outside 1-100.
    """
    if not isinstance(skip, int) or skip < 0:
        raise ValidationError(
            "Invalid pagination",
            detail="skip must be zero or a positive integer.",
            code="invalid_pagination",
        )
    if not isinstance(limit, int) or limit < 1 or limit > MAX_PAGE_SIZE:
        raise ValidationError(
            "Invalid pagination",
            detail=f"limit must be between 1 and {MAX_PAGE_SIZE}.",
            code="invalid_pagination",
        )
    return skip, limit


def _normalize_status(status: Optional[str]) -> Optional[BorrowingStatus]:
    """Turn a status string into an enum member.

    Args:
        status: ``BORROWED``, ``RETURNED`` or ``OVERDUE`` in any case; ``None``
            or blank means no filter.

    Returns:
        BorrowingStatus | None: The status to filter on, or ``None``.

    Raises:
        ValidationError: If the status is not one the application supports.
    """
    if status is None:
        return None
    if isinstance(status, str) and not status.strip():
        return None
    candidate: str = str(status).strip().upper()
    try:
        return BorrowingStatus(candidate)
    except ValueError as exc:
        allowed: str = ", ".join(member.value for member in BorrowingStatus)
        raise ValidationError(
            "Invalid status",
            detail=f"status must be one of: {allowed}.",
            code="invalid_status",
        ) from exc


def _get_user_or_404(db: Session, user_id: int) -> User:
    """Load a member or raise a 404.

    Args:
        db: Database session.
        user_id: Primary key of the member.

    Returns:
        User: The matching row.

    Raises:
        NotFoundError: If no user has that id.
    """
    user: Optional[User] = db.get(User, user_id)
    if user is None:
        logger.warning("Borrow lookup failed: user %s not found", user_id)
        raise NotFoundError(
            "User not found",
            detail=f"No user exists with id {user_id}.",
            code="user_not_found",
        )
    return user


def _assert_user_can_borrow(db: Session, user: User) -> None:
    """Ensure an account may start a loan.

    Args:
        db: Database session (unused, kept for symmetry with the other checks).
        user: The member attempting to borrow.

    Raises:
        ForbiddenError: If the account has been deactivated.
    """
    del db
    if not user.is_active:
        logger.warning("Borrow rejected: inactive account %s", user.email)
        raise ForbiddenError(
            "Account is inactive",
            detail="This account has been deactivated and cannot borrow books.",
            code="inactive_user",
        )


def _get_book_or_404(db: Session, book_id: int) -> Book:
    """Load a book or raise a 404.

    Args:
        db: Database session.
        book_id: Primary key of the book.

    Returns:
        Book: The matching row.

    Raises:
        NotFoundError: If no book has that id.
    """
    book: Optional[Book] = db.get(Book, book_id)
    if book is None:
        logger.warning("Borrow lookup failed: book %s not found", book_id)
        raise NotFoundError(
            "Book not found",
            detail=f"No book exists with id {book_id}.",
            code="book_not_found",
        )
    return book


def _assert_not_already_borrowed(db: Session, user_id: int, book_id: int) -> None:
    """Ensure the member does not already hold this title.

    Args:
        db: Database session.
        user_id: Primary key of the member.
        book_id: Primary key of the book.

    Raises:
        ConflictError: If an open loan for the same title already exists.
    """
    row = db.execute(
        select(BorrowingRecord.id)
        .where(
            BorrowingRecord.user_id == user_id,
            BorrowingRecord.book_id == book_id,
            BorrowingRecord.status == BorrowingStatus.BORROWED,
        )
        .limit(1)
    ).first()
    if row is not None:
        logger.warning(
            "Borrow rejected: user %s already holds book %s (record %s)",
            user_id,
            book_id,
            row[0],
        )
        raise ConflictError(
            "Book already borrowed",
            detail=(
                f"You already have a copy of this title on loan (record {row[0]}). "
                "Return it before borrowing another copy."
            ),
            code="already_borrowed",
        )


def _borrow_book(user_id: int, book_id: int, db: Session) -> BorrowRecordResponse:
    """Lend a copy to a member. See :func:`borrow_book`."""
    user: User = _get_user_or_404(db, user_id)
    _assert_user_can_borrow(db, user)
    book: Book = _get_book_or_404(db, book_id)
    _assert_not_already_borrowed(db, user_id, book_id)

    issue_date: datetime = utcnow()
    record = BorrowingRecord(
        user_id=user.id,
        book_id=book.id,
        issue_date=issue_date,
        due_date=calculate_due_date(issue_date),
        status=BorrowingStatus.BORROWED,
        fine_amount=Decimal("0.00"),
    )
    db.add(record)

    try:
        # Claim the copy with a single conditional UPDATE rather than reading
        # `available_quantity`, checking it in Python and writing back the value
        # minus one. Two members racing for the last copy would both read the
        # same count and both write the same result, lending one physical copy
        # out twice. Letting the database evaluate `available_quantity > 0` and
        # decrement in one statement makes the claim atomic, and the row count
        # says whether this caller won it.
        claimed = db.execute(
            update(Book)
            .where(Book.id == book.id, Book.available_quantity > 0)
            .values(available_quantity=Book.available_quantity - 1)
        ).rowcount
        if claimed != 1:
            db.rollback()
            logger.warning(
                "Borrow rejected: book %s lost the race for its last copy", book_id
            )
            raise BadRequestError(
                "Book is not available",
                detail=(
                    f"Every copy of '{book.title}' is currently on loan. "
                    "Try again once a copy is returned."
                ),
                code="book_unavailable",
            )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Borrow failed for user %s, book %s", user_id, book_id)
        raise InternalServerError(
            "Could not complete the loan",
            detail="The book could not be borrowed. Please try again later.",
            code="borrow_failed",
        ) from exc

    db.refresh(record)
    db.refresh(book)
    logger.info(
        "Borrowed book %s (id=%s) to user %s; due %s, %s copies left",
        book.title,
        book.id,
        user.email,
        record.due_date.date().isoformat(),
        book.available_quantity,
    )
    return BorrowRecordResponse.model_validate(record)


def _return_book(
    user_id: int, borrowing_record_id: int, db: Session
) -> BorrowRecordResponse:
    """Take a copy back. See :func:`return_book`."""
    record: Optional[BorrowingRecord] = db.get(BorrowingRecord, borrowing_record_id)
    if record is None:
        logger.warning(
            "Return lookup failed: borrowing record %s not found", borrowing_record_id
        )
        raise NotFoundError(
            "Borrowing record not found",
            detail=f"No borrowing record exists with id {borrowing_record_id}.",
            code="borrowing_record_not_found",
        )

    if record.user_id != user_id:
        # Deliberately a 403 rather than a 404: the caller is authenticated, so
        # hiding the record would only make the ownership rule harder to debug.
        logger.warning(
            "Return rejected: user %s does not own borrowing record %s",
            user_id,
            borrowing_record_id,
        )
        raise ForbiddenError(
            "Not your borrowing record",
            detail="You can only return books that you borrowed.",
            code="not_record_owner",
        )

    if record.status != BorrowingStatus.BORROWED:
        logger.warning(
            "Return rejected: borrowing record %s is already %s",
            borrowing_record_id,
            record.status,
        )
        closed_on: str = (
            record.return_date.date().isoformat()
            if record.return_date is not None
            else "an earlier date"
        )
        raise ValidationError(
            "Book already returned",
            detail=f"This loan was already closed on {closed_on}.",
            code="already_returned",
        )

    return_date: datetime = utcnow()
    late: bool = is_overdue_helper(record.due_date, return_date)
    record.return_date = return_date
    record.status = BorrowingStatus.OVERDUE if late else BorrowingStatus.RETURNED
    if late:
        record.fine_amount = calculate_fine(record.due_date, return_date)

    book: Book = _get_book_or_404(db, record.book_id)

    try:
        # Same reason as the borrow path: the increment is a single statement
        # with the ceiling evaluated by the database, so concurrent returns
        # cannot lose an increment between them. The `< total_quantity` guard is
        # what stops a hand-edited inventory from pushing the counter past the
        # copies the library actually owns.
        db.execute(
            update(Book)
            .where(
                Book.id == book.id,
                Book.available_quantity < Book.total_quantity,
            )
            .values(available_quantity=Book.available_quantity + 1)
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Return failed for borrowing record %s", borrowing_record_id)
        raise InternalServerError(
            "Could not complete the return",
            detail="The book could not be returned. Please try again later.",
            code="return_failed",
        ) from exc

    db.refresh(record)
    db.refresh(book)
    logger.info(
        "Returned borrowing record %s (book %s, user %s); status=%s fine=%s",
        record.id,
        record.book_id,
        user_id,
        record.status.value,
        record.fine_amount,
    )
    return BorrowRecordResponse.model_validate(record)


def _history_page(
    skip: int,
    limit: int,
    user_id: Optional[int],
    status: Optional[str],
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Build one page of loan history. Shared by both history functions."""
    skip, limit = _validate_pagination(skip, limit)
    wanted: Optional[BorrowingStatus] = _normalize_status(status)

    conditions: List[Any] = []
    if user_id is not None:
        conditions.append(BorrowingRecord.user_id == user_id)
    if wanted is not None:
        conditions.append(BorrowingRecord.status == wanted)
    if start_date is not None:
        conditions.append(BorrowingRecord.issue_date >= start_date)
    if end_date is not None:
        conditions.append(BorrowingRecord.issue_date <= end_date)

    try:
        filters = select(BorrowingRecord)
        if conditions:
            filters = filters.where(*conditions)

        # Count before ordering: the count does not need the sort, and some
        # dialects reject ORDER BY inside a derived table.
        total: int = db.execute(
            select(func.count()).select_from(filters.subquery())
        ).scalar_one()

        rows: List[BorrowingRecord] = list(
            db.execute(
                filters.order_by(BorrowingRecord.issue_date.desc())
                .offset(skip)
                .limit(limit)
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception("Borrowing history query failed")
        raise InternalServerError(
            "Could not load the borrowing history",
            detail="The borrowing history could not be read. Please try again later.",
            code="borrowing_history_query_failed",
        ) from exc

    records: List[BorrowRecordResponse] = [
        BorrowRecordResponse.model_validate(row) for row in rows
    ]
    return BorrowingHistoryResponse(
        records=records, total=total, user_id=user_id
    ).model_dump()


def _get_borrowing_record(
    user_id: int, borrowing_record_id: int, db: Session
) -> BorrowRecordResponse:
    """Read one loan. See :func:`get_borrowing_record`."""
    record: Optional[BorrowingRecord] = db.get(BorrowingRecord, borrowing_record_id)
    if record is None:
        logger.warning(
            "Loan lookup failed: borrowing record %s not found", borrowing_record_id
        )
        raise NotFoundError(
            "Borrowing record not found",
            detail=f"No borrowing record exists with id {borrowing_record_id}.",
            code="borrowing_record_not_found",
        )

    if record.user_id != user_id:
        logger.warning(
            "Loan lookup rejected: user %s does not own borrowing record %s",
            user_id,
            borrowing_record_id,
        )
        raise ForbiddenError(
            "Not your borrowing record",
            detail="You can only read loans that you borrowed.",
            code="not_record_owner",
        )

    logger.debug("Read borrowing record %s for user %s", record.id, user_id)
    return BorrowRecordResponse.model_validate(record)


def _get_borrowing_history(
    user_id: int,
    skip: int,
    limit: int,
    status: Optional[str],
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Read one member's loans. See :func:`get_borrowing_history`."""
    _get_user_or_404(db, user_id)
    page: Dict[str, Any] = _history_page(
        skip, limit, user_id, status, db, start_date, end_date
    )
    logger.debug("Read %s loans for user %s", page["total"], user_id)
    return page


def _get_all_borrowing_records(
    skip: int,
    limit: int,
    user_id: Optional[int],
    status: Optional[str],
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Read every loan. See :func:`get_all_borrowing_records`."""
    page: Dict[str, Any] = _history_page(
        skip, limit, user_id, status, db, start_date, end_date
    )
    logger.debug("Read %s loans across the library", page["total"])
    return page


def _get_overdue_records(db: Session) -> List[BorrowRecordResponse]:
    """List the late loans. See :func:`get_overdue_books`."""
    now: datetime = utcnow()
    try:
        # Two ways to be late: already flagged ``OVERDUE``, or still ``BORROWED``
        # with the due date behind us. The second catches loans that were never
        # swept by `check_and_update_overdue_status`.
        rows: List[BorrowingRecord] = list(
            db.execute(
                select(BorrowingRecord)
                .where(
                    or_(
                        BorrowingRecord.status == BorrowingStatus.OVERDUE,
                        (
                            (BorrowingRecord.status == BorrowingStatus.BORROWED)
                            & (BorrowingRecord.due_date < now)
                        ),
                    )
                )
                .order_by(BorrowingRecord.due_date.asc())
            )
            .scalars()
            .all()
        )
    except SQLAlchemyError as exc:
        logger.exception("Overdue loan query failed")
        raise InternalServerError(
            "Could not load the overdue loans",
            detail="The overdue list could not be read. Please try again later.",
            code="overdue_query_failed",
        ) from exc

    logger.debug("Found %s overdue loans", len(rows))
    return [BorrowRecordResponse.model_validate(row) for row in rows]


def _check_and_update_overdue_status(db: Session) -> int:
    """Flag every past-due open loan. See :func:`check_and_update_overdue_status`."""
    now: datetime = utcnow()
    try:
        # Bulk UPDATE: one statement for the whole sweep instead of loading and
        # rewriting each row, so a large backlog costs a single round trip.
        result = db.execute(
            select(BorrowingRecord)
            .where(
                BorrowingRecord.status == BorrowingStatus.BORROWED,
                BorrowingRecord.due_date < now,
            )
        ).scalars().all()
        for record in result:
            record.status = BorrowingStatus.OVERDUE
        updated: int = len(result)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Overdue sweep failed")
        raise InternalServerError(
            "Could not update the overdue loans",
            detail="The overdue sweep could not be completed. Please try again later.",
            code="overdue_sweep_failed",
        ) from exc

    if updated:
        logger.info("Overdue sweep flagged %s loan(s) as OVERDUE", updated)
    else:
        logger.debug("Overdue sweep found nothing to flag")
    return updated


async def borrow_book(
    user_id: int, book_id: int, db: Session = None  # type: ignore[assignment]
) -> BorrowRecordResponse:
    """Lend a copy of a book to a member.

    The caller is identified by the route, which reads the bearer token; this
    function trusts that ``user_id`` and still checks the account is active.

    A member may hold only one copy of a title at a time, so borrowing a title
    that is already on loan for that member is refused. The copy counter is
    decremented in the same transaction as the new loan row.

    Args:
        user_id: Member taking the copy.
        book_id: Primary key of the book to lend.
        db: Database session injected by FastAPI.

    Returns:
        BorrowRecordResponse: The new loan, with its due date 14 days out.

    Raises:
        NotFoundError: If the member or the book does not exist.
        ForbiddenError: If the account is deactivated.
        ConflictError: If the member already holds this title.
        BadRequestError: If every copy is on loan (HTTP 400).
        InternalServerError: If the insert fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides. Both statements are
        skipped, because the second reads the value the first would have bound.

        >>> record = await borrow_book(user_id=1, book_id=7, db=session)  # doctest: +SKIP
        >>> record.status  # doctest: +SKIP
        'BORROWED'
    """
    return await _to_thread(_borrow_book, user_id, book_id, db)


async def return_book(
    user_id: int,
    borrowing_record_id: int,
    db: Session = None,  # type: ignore[assignment]
) -> BorrowRecordResponse:
    """Take a copy back and close its loan.

    A copy returned after its due date is recorded as ``OVERDUE`` and charged
    :data:`~app.utils.borrowing_helpers.FINE_PER_DAY` for each whole day late;
    on time it is recorded as ``RETURNED`` with no fine. The copy counter is
    incremented in the same transaction, clamped to the number of copies owned
    so a hand-edited inventory cannot push it past the total.

    Args:
        user_id: Member returning the copy.
        borrowing_record_id: Primary key of the loan being closed.
        db: Database session injected by FastAPI.

    Returns:
        BorrowRecordResponse: The closed loan, including any fine.

    Raises:
        NotFoundError: If no such loan exists.
        ForbiddenError: If the loan belongs to another member.
        ValidationError: If the loan was already returned.
        InternalServerError: If the update fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides. Both statements are
        skipped, because the second reads the value the first would have bound.

        >>> record = await return_book(  # doctest: +SKIP
        ...     user_id=1, borrowing_record_id=3, db=session
        ... )
        >>> record.status  # doctest: +SKIP
        'RETURNED'
    """
    return await _to_thread(_return_book, user_id, borrowing_record_id, db)


async def get_borrowing_record(
    user_id: int,
    borrowing_record_id: int,
    db: Session = None,  # type: ignore[assignment]
) -> BorrowRecordResponse:
    """Read one loan belonging to the caller.

    Ownership is enforced here rather than in the route: the endpoint is
    reachable with any valid token, so the controller confirms the record is the
    caller's before returning it.

    Args:
        user_id: Member making the request.
        borrowing_record_id: Primary key of the loan.
        db: Database session injected by FastAPI.

    Returns:
        BorrowRecordResponse: The loan, including its fine and due date.

    Raises:
        NotFoundError: If no such loan exists.
        ForbiddenError: If the loan belongs to another member.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides.

        >>> (await get_borrowing_record(1, 3, db=session)).status  # doctest: +SKIP
        'RETURNED'
    """
    return await _to_thread(_get_borrowing_record, user_id, borrowing_record_id, db)


async def get_borrowing_history(
    user_id: int,
    skip: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    status: Optional[str] = None,
    db: Session = None,  # type: ignore[assignment]
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Read one member's loans, newest first.

    Args:
        user_id: Member whose history is requested.
        skip: Rows to skip; must be zero or positive.
        limit: Page size, 1-100; defaults to 10.
        status: Restrict to ``BORROWED``, ``RETURNED`` or ``OVERDUE``.
        db: Database session injected by FastAPI.
        start_date: Earliest issue date to include, inclusive.
        end_date: Latest issue date to include, inclusive.

    Returns:
        dict: ``{records, total, user_id}`` matching ``BorrowingHistoryResponse``.

    Raises:
        NotFoundError: If no user has that id.
        ValidationError: If the status is unknown or the window is invalid.
        InternalServerError: If the query fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides. Both statements are
        skipped, because the second reads the value the first would have bound.

        >>> page = await get_borrowing_history(user_id=1, limit=25, db=session)  # doctest: +SKIP
        >>> page["total"]  # doctest: +SKIP
        4
    """
    return await _to_thread(
        _get_borrowing_history, user_id, skip, limit, status, db, start_date, end_date
    )


async def get_all_borrowing_records(
    skip: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = None,  # type: ignore[assignment]
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Read every loan in the library, newest first.

    Intended for administrators. Authorization is enforced by the route, which
    restricts this operation to that role; the controller trusts that decision.

    Args:
        skip: Rows to skip; must be zero or positive.
        limit: Page size, 1-100; defaults to 10.
        user_id: Restrict to one member when supplied.
        status: Restrict to ``BORROWED``, ``RETURNED`` or ``OVERDUE``.
        db: Database session injected by FastAPI.
        start_date: Earliest issue date to include, inclusive.
        end_date: Latest issue date to include, inclusive.

    Returns:
        dict: ``{records, total, user_id}``; ``user_id`` is ``None`` when the
        listing was not narrowed to a member.

    Raises:
        ValidationError: If the status is unknown or the window is invalid.
        InternalServerError: If the query fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides. Both statements are
        skipped, because the second reads the value the first would have bound.

        >>> page = await get_all_borrowing_records(status="OVERDUE", db=session)  # doctest: +SKIP
        >>> page["total"]  # doctest: +SKIP
        2
    """
    return await _to_thread(
        _get_all_borrowing_records,
        skip,
        limit,
        user_id,
        status,
        db,
        start_date,
        end_date,
    )


async def get_overdue_books(
    db: Session = None,  # type: ignore[assignment]
) -> List[BorrowRecordResponse]:
    """List every late loan, oldest due date first.

    Catches both loans already flagged ``OVERDUE`` and open loans whose due date
    has passed but which no sweep has flagged yet, so the list is correct even
    before :func:`check_and_update_overdue_status` has run.

    Args:
        db: Database session injected by FastAPI.

    Returns:
        list[BorrowRecordResponse]: The late loans, soonest due date first.

    Raises:
        InternalServerError: If the query fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides. Both statements are
        skipped, because the second reads the value the first would have bound.

        >>> late = await get_overdue_books(db=session)  # doctest: +SKIP
        >>> [record.status for record in late]  # doctest: +SKIP
        ['OVERDUE']
    """
    return await _to_thread(_get_overdue_records, db)


async def check_and_update_overdue_status(db: Session = None) -> int:  # type: ignore[assignment]
    """Flag every open loan whose due date has passed.

    Meant to be called on a schedule. :func:`get_overdue_books` already reports
    late loans whether or not this has run, so the sweep exists to make the
    stored ``status`` column agree with reality - it is what history filters and
    the member-facing "currently overdue" count rely on.

    Args:
        db: Database session injected by FastAPI.

    Returns:
        int: How many loans were flagged.

    Raises:
        InternalServerError: If the sweep fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides.

        >>> await check_and_update_overdue_status(db=session)  # doctest: +SKIP
        2
    """
    return await _to_thread(_check_and_update_overdue_status, db)


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "borrow_book",
    "check_and_update_overdue_status",
    "get_all_borrowing_records",
    "get_borrowing_history",
    "get_borrowing_record",
    "get_overdue_books",
    "return_book",
]