"""Book return API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers import borrow_controller
from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.borrowing_schema import ReturnResponseSchema

router = APIRouter(prefix="/return", tags=["Return"])


@router.post(
    "/{borrowing_id}",
    response_model=ReturnResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Return a borrowed book",
)
def return_book(
    borrowing_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReturnResponseSchema:
    """Return a currently borrowed book for the authenticated user.

    Args:
        borrowing_id: Primary key of the borrowing record to return.
        current_user: Authenticated member resolved from JWT bearer token.
        db: Database session.

    Returns:
        ReturnResponseSchema: Summary of borrowing return transaction and fine.
    """
    return borrow_controller.return_book(db, current_user, borrowing_id)
