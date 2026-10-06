"""Borrowing, return, and history business logic with database transaction management."""

from __future__ import annotations

import math
import threading
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User
from app.schemas.borrowing_schema import (
    BorrowResponseSchema,
    BorrowingHistoryItem,
    BorrowingHistoryResponse,
    ReturnResponseSchema,
)
from app.utils.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError

_borrow_transaction_lock = threading.Lock()


def borrow_book(db: Session, user: User, book_id: int) -> BorrowResponseSchema:
    """Borrow a book for an authenticated user within a database transaction.

    Args:
        db: Active database session.
        user: Authenticated user issuing the request.
        book_id: Primary key of the target book.

    Returns:
        BorrowResponseSchema: Summary of the created borrowing record.

    Raises:
        NotFoundError: If the requested book does not exist.
        BadRequestError: If the book has no available copies remaining.
        ConflictError: If the user already has an active borrowing record for this book.
    """
    with _borrow_transaction_lock:
        try:
            # 1. Fetch and acquire exclusive row lock on the target book
            statement = select(Book).where(Book.id == book_id).with_for_update()
            book: Book | None = db.execute(statement).scalar_one_or_none()

            if book is None:
                raise NotFoundError("Book not found", code="book_not_found")

            # 2. Check available quantity
            if book.available_quantity <= 0:
                raise BadRequestError("Book is currently unavailable for borrowing", code="book_unavailable")

            # 3. Check if user already has an active borrowing for this book
            active_statement = select(BorrowingRecord).where(
                BorrowingRecord.user_id == user.id,
                BorrowingRecord.book_id == book_id,
                BorrowingRecord.status == BorrowingStatus.BORROWED,
                BorrowingRecord.return_date.is_(None),
            )
            existing_active = db.execute(active_statement).scalar_one_or_none()

            if existing_active is not None:
                raise ConflictError(
                    "User already has an active borrowing record for this book",
                    code="already_borrowed",
                )

            # 4. Decrement available quantity by 1
            book.available_quantity -= 1

            # 5. Create BorrowingRecord
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            due_date = now + timedelta(days=settings.default_borrow_days)

            record = BorrowingRecord(
                user_id=user.id,
                book_id=book.id,
                issue_date=now,
                due_date=due_date,
                return_date=None,
                status=BorrowingStatus.BORROWED,
                fine_amount=Decimal("0.00"),
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            db.refresh(book)

            return BorrowResponseSchema(
                id=record.id,
                book_id=book.id,
                book_title=book.title,
                issue_date=record.issue_date,
                due_date=record.due_date,
                return_date=record.return_date,
                status=record.status,
                fine_amount=record.fine_amount,
                remaining_available_quantity=book.available_quantity,
                message="Book borrowed successfully",
            )
        except Exception:
            db.rollback()
            raise


def return_book(db: Session, user: User, borrowing_id: int) -> ReturnResponseSchema:
    """Return a borrowed book for an authenticated user within a database transaction.

    Args:
        db: Active database session.
        user: Authenticated user issuing the return request.
        borrowing_id: Primary key of the borrowing record.

    Returns:
        ReturnResponseSchema: Summary of the returned borrowing record and fine.

    Raises:
        NotFoundError: If the borrowing record or associated book does not exist.
        PermissionDeniedError: If the borrowing record belongs to another user.
        BadRequestError: If the borrowing record is already returned or inventory would overflow.
    """
    with _borrow_transaction_lock:
        try:
            # 1. Fetch and acquire exclusive row lock on the target BorrowingRecord
            statement = (
                select(BorrowingRecord)
                .where(BorrowingRecord.id == borrowing_id)
                .with_for_update()
            )
            record: BorrowingRecord | None = db.execute(statement).scalar_one_or_none()

            if record is None:
                raise NotFoundError("Borrowing record not found", code="record_not_found")

            # 2. Authorization check: ensure record belongs to the authenticated user
            if record.user_id != user.id:
                raise PermissionDeniedError(
                    "You are not authorized to return this borrowing record",
                    code="unauthorized_return",
                )

            # 3. Check if already returned
            if record.status == BorrowingStatus.RETURNED or record.return_date is not None:
                raise BadRequestError(
                    "Borrowing record has already been returned",
                    code="already_returned",
                )

            # 4. Fetch and acquire exclusive row lock on the associated Book
            book_statement = (
                select(Book)
                .where(Book.id == record.book_id)
                .with_for_update()
            )
            book: Book | None = db.execute(book_statement).scalar_one_or_none()

            if book is None:
                raise NotFoundError("Associated book not found", code="book_not_found")

            # 5. Inventory sanity check: prevent available_quantity from exceeding total_quantity
            if book.available_quantity + 1 > book.total_quantity:
                raise BadRequestError(
                    "Cannot return book: available quantity would exceed total quantity",
                    code="inventory_overflow",
                )

            # 6. Calculate return timestamp and fine amount
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            fine_amount = Decimal("0.00")

            if now > record.due_date:
                overdue_seconds = (now - record.due_date).total_seconds()
                overdue_days = int(overdue_seconds // 86400)
                if overdue_days == 0 and overdue_seconds > 0:
                    overdue_days = 1
                if overdue_days > 0:
                    fine_amount = Decimal(str(overdue_days)) * settings.daily_fine_rate_decimal

            # 7. Update BorrowingRecord and Book fields
            record.return_date = now
            record.status = BorrowingStatus.RETURNED
            record.fine_amount = fine_amount
            book.available_quantity += 1

            # 8. Commit transaction
            db.commit()
            db.refresh(record)
            db.refresh(book)

            return ReturnResponseSchema(
                id=record.id,
                book_id=book.id,
                book_title=book.title,
                issue_date=record.issue_date,
                due_date=record.due_date,
                return_date=record.return_date,
                status=record.status,
                fine_amount=record.fine_amount,
                remaining_available_quantity=book.available_quantity,
                message="Book returned successfully",
            )
        except Exception:
            db.rollback()
            raise


def get_user_borrowing_history(
    db: Session,
    user: User,
    page: int = 1,
    page_size: int = 10,
    status: Optional[BorrowingStatus] = None,
) -> BorrowingHistoryResponse:
    """Retrieve paginated borrowing history for an authenticated user.

    Args:
        db: Active database session.
        user: Authenticated user issuing the request.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        status: Optional status filter (BORROWED, RETURNED, OVERDUE).

    Returns:
        BorrowingHistoryResponse: Paginated list of borrowing records with book details.

    Raises:
        BadRequestError: If page or page_size parameters are invalid.
    """
    if page < 1:
        raise BadRequestError("Page number must be greater than or equal to 1", code="invalid_page")
    if page_size < 1 or page_size > 100:
        raise BadRequestError("Page size must be between 1 and 100", code="invalid_page_size")

    count_stmt = select(func.count(BorrowingRecord.id)).where(BorrowingRecord.user_id == user.id)
    if status is not None:
        count_stmt = count_stmt.where(BorrowingRecord.status == status)

    total: int = db.execute(count_stmt).scalar() or 0

    if total == 0:
        return BorrowingHistoryResponse(
            items=[],
            page=page,
            page_size=page_size,
            total=0,
        )

    query = (
        select(BorrowingRecord)
        .options(joinedload(BorrowingRecord.book))
        .where(BorrowingRecord.user_id == user.id)
    )

    if status is not None:
        query = query.where(BorrowingRecord.status == status)

    query = query.order_by(BorrowingRecord.issue_date.desc(), BorrowingRecord.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    records = db.execute(query).scalars().all()

    items = [
        BorrowingHistoryItem.model_validate(rec)
        for rec in records
    ]

    return BorrowingHistoryResponse(
        items=items,
        page=page,
        page_size=page_size,
        total=total,
    )
