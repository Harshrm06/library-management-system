"""Borrowing API endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.controllers import borrow_controller
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.borrowing_record import BorrowingStatus
from app.models.user import User
from app.schemas.borrowing_schema import BorrowResponseSchema, BorrowingHistoryResponse

router = APIRouter(prefix="/borrow", tags=["Borrowing"])


@router.get(
    "/history",
    response_model=BorrowingHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated member's borrowing history",
)
def get_borrowing_history(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    status: Optional[BorrowingStatus] = Query(default=None, description="Optional status filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowingHistoryResponse:
    """Retrieve paginated borrowing history for the authenticated user.

    Args:
        page: Page number.
        page_size: Items per page.
        status: Optional status filter (BORROWED, RETURNED, OVERDUE).
        current_user: Authenticated member resolved from JWT bearer token.
        db: Database session.

    Returns:
        BorrowingHistoryResponse: Paginated list of borrowing records with book details.
    """
    return borrow_controller.get_user_borrowing_history(
        db, current_user, page=page, page_size=page_size, status=status
    )


@router.post(
    "/{book_id}",
    response_model=BorrowResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Borrow a book",
)
def borrow_book(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowResponseSchema:
    """Borrow an available book for the authenticated member.

    Args:
        book_id: ID of the book to borrow.
        current_user: Authenticated member resolved from JWT bearer token.
        db: Database session.

    Returns:
        BorrowResponseSchema: Summary of borrowing transaction and updated stock.
    """
    return borrow_controller.borrow_book(db, current_user, book_id)
