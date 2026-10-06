"""Borrowing endpoints.

The router is mounted at ``/api`` (built from ``settings.api_v1_prefix`` so the
mount point stays configurable) and every error raised by the controller is
converted into the ``ErrorResponse`` envelope by the handlers registered in
:mod:`app.main`.

Endpoints:
    * ``POST /api/borrow``                    - lend a copy to the caller
    * ``POST /api/return``                    - take a copy back
    * ``GET  /api/borrow/{id}``               - read one of the caller's loans
    * ``GET  /api/borrowing-history``         - the caller's own history
    * ``GET  /api/borrowing-history/all``     - every loan (admin)
    * ``GET  /api/overdue-books``             - late loans (admin)

Every endpoint depends on :func:`app.middleware.auth_middleware.get_current_user`
or :func:`~app.middleware.auth_middleware.require_admin`, and no endpoint accepts
a caller-supplied user id: the member always comes from the bearer token, so a
client cannot borrow, return or read on someone else's behalf.

The two history paths are declared before ``/api/borrow/{borrowing_record_id}``
would otherwise shadow them, so ``all`` and the paginated query string are never
mistaken for a record id.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.controllers import borrowing_controller
from app.database import get_db
from app.middleware.auth_middleware import get_current_user, require_admin
from app.routes.auth_routes import error_responses
from app.schemas.borrowing_record_schema import (
    BorrowRecordResponse,
    BorrowingHistoryResponse,
    BorrowRequest,
    ReturnRequest,
)

router = APIRouter(
    prefix=settings.api_v1_prefix,
    tags=["borrowing"],
)

BORROW_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "borrow_a_copy": {
                        "summary": "Borrow one copy of a catalogued title",
                        "value": {"book_id": 7},
                    }
                }
            }
        }
    }
}

RETURN_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "return_a_copy": {
                        "summary": (
                            "Return the copy behind loan 3; a member may hold "
                            "several copies of one title, so the loan is named "
                            "rather than the book"
                        ),
                        "value": {"borrowing_record_id": 3},
                    }
                }
            }
        }
    }
}


def _history_filters(
    skip: int,
    limit: int,
    status_filter: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> Dict[str, Any]:
    """Assemble the keyword arguments shared by both history endpoints.

    Args:
        skip: Rows to skip.
        limit: Page size.
        status_filter: Status to restrict to, or ``None`` for every status.
        start_date: Earliest issue date to include.
        end_date: Latest issue date to include.

    Returns:
        dict: Keyword arguments for the controller call.
    """
    return {
        "skip": skip,
        "limit": limit,
        "status": status_filter,
        "start_date": start_date,
        "end_date": end_date,
    }


@router.post(
    "/borrow",
    response_model=BorrowRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Borrow a book",
    description=(
        "Lends one copy of a catalogued title to the authenticated member and "
        "records the loan. The due date is set by the server to 14 days after "
        "the issue date, so a client cannot forge it. A member may hold only "
        "one copy of a title at a time; a second borrow of the same title is "
        "refused with 409 Conflict. When every copy is on loan the request is "
        "refused with 400 Bad Request. The member always comes from the bearer "
        "token."
    ),
    responses=error_responses(400, 403, 404, 409, 422),
    openapi_extra=BORROW_REQUEST_EXAMPLE,
)
async def borrow_book(
    payload: BorrowRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    """Lend a copy of a book to the caller.

    Args:
        payload: The title to borrow, named by `book_id`.
        current_user: The authenticated member, resolved by `get_current_user`.
        db: Database session dependency.

    Returns:
        BorrowRecordResponse: 201 with the new loan and its due date.

    Raises:
        UnauthorizedError: If no valid token was supplied (401).
        ForbiddenError: If the account is deactivated (403).
        NotFoundError: If the member or the book does not exist (404).
        ConflictError: If the member already holds this title (409).
        BadRequestError: If every copy is on loan (400).
        InternalServerError: If the insert fails (500).
    """
    return await borrowing_controller.borrow_book(
        user_id=int(current_user["id"]),
        book_id=payload.book_id,
        db=db,
    )


@router.post(
    "/return",
    response_model=BorrowRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Return a borrowed book",
    description=(
        "Closes one of the caller's loans and puts the copy back on the shelf. "
        "A copy returned after its due date is recorded as `OVERDUE` and "
        "charged 10 per day for every whole day late; on time it is recorded as "
        "`RETURNED` with no fine. Returning an already returned loan is "
        "refused, and a loan belonging to another member is refused with 403."
    ),
    responses=error_responses(403, 404, 422),
    openapi_extra=RETURN_REQUEST_EXAMPLE,
)
async def return_book(
    payload: ReturnRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    """Take a borrowed copy back.

    Args:
        payload: The loan being closed, named by `borrowing_record_id`.
        current_user: The authenticated member, resolved by `get_current_user`.
        db: Database session dependency.

    Returns:
        BorrowRecordResponse: 200 with the closed loan and any fine.

    Raises:
        UnauthorizedError: If no valid token was supplied (401).
        ForbiddenError: If the loan belongs to another member (403).
        NotFoundError: If no such loan exists (404).
        ValidationError: If the loan was already returned (422).
        InternalServerError: If the update fails (500).
    """
    return await borrowing_controller.return_book(
        user_id=int(current_user["id"]),
        borrowing_record_id=payload.borrowing_record_id,
        db=db,
    )


@router.get(
    "/borrowing-history",
    response_model=BorrowingHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read the caller's borrowing history",
    description=(
        "Returns one page of the authenticated member's loans, newest issue "
        "date first. `status` restricts the page to `BORROWED`, `RETURNED` or "
        "`OVERDUE`, and `start_date`/`end_date` bound the issue date as an "
        "inclusive range. `skip` and `limit` select the window (`limit` is "
        "capped at 100). Administrators see their own loans here too; use "
        "`/api/borrowing-history/all` for the whole library."
    ),
    responses=error_responses(403, 404, 422),
)
async def read_borrowing_history(
    skip: int = Query(default=0, ge=0, description="Rows to skip, for offset paging"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum rows to return, 1-100"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Restrict to BORROWED, RETURNED or OVERDUE",
        examples=["OVERDUE"],
    ),
    start_date: Optional[datetime] = Query(
        default=None,
        description="Earliest issue date to include, inclusive",
        examples=["2026-01-01T00:00:00"],
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Latest issue date to include, inclusive",
        examples=["2026-12-31T23:59:59"],
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return a page of the caller's loans.

    Args:
        skip: Rows to skip; must be zero or positive.
        limit: Page size, 1-100; defaults to 10.
        status_filter: Status to restrict to, bound to the `status` query name.
        start_date: Earliest issue date to include.
        end_date: Latest issue date to include.
        current_user: The authenticated member, resolved by `get_current_user`.
        db: Database session dependency.

    Returns:
        dict: 200 with `{records, total, user_id}`.

    Raises:
        UnauthorizedError: If no valid token was supplied (401).
        NotFoundError: If the token refers to a user that no longer exists (404).
        ValidationError: If the status is unknown or the window is invalid (422).
        InternalServerError: If the query fails (500).
    """
    filters: Dict[str, Any] = _history_filters(
        skip, limit, status_filter, start_date, end_date
    )
    return await borrowing_controller.get_borrowing_history(
        user_id=int(current_user["id"]),
        db=db,
        **filters,
    )


@router.get(
    "/borrowing-history/all",
    response_model=BorrowingHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Read every loan in the library",
    description=(
        "Admin only. Returns one page of loans across all members, newest "
        "issue date first. `user_id` narrows the page to a single member, "
        "while `status`, `start_date` and `end_date` filter as they do on the "
        "member endpoint. `user_id` is `null` in the response when the page was "
        "not narrowed to one member."
    ),
    responses=error_responses(403, 422),
)
async def read_all_borrowing_records(
    skip: int = Query(default=0, ge=0, description="Rows to skip, for offset paging"),
    limit: int = Query(default=10, ge=1, le=100, description="Maximum rows to return, 1-100"),
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Restrict to BORROWED, RETURNED or OVERDUE",
        examples=["BORROWED"],
    ),
    user_id: Optional[int] = Query(
        default=None,
        ge=1,
        description="Restrict to one member",
        examples=[1],
    ),
    start_date: Optional[datetime] = Query(
        default=None,
        description="Earliest issue date to include, inclusive",
        examples=["2026-01-01T00:00:00"],
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="Latest issue date to include, inclusive",
        examples=["2026-12-31T23:59:59"],
    ),
    _admin: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return a page of loans across the whole library.

    Args:
        skip: Rows to skip; must be zero or positive.
        limit: Page size, 1-100; defaults to 10.
        status_filter: Status to restrict to, bound to the `status` query name.
        user_id: Restrict to one member when supplied.
        start_date: Earliest issue date to include.
        end_date: Latest issue date to include.
        _admin: The authenticated administrator, resolved by `require_admin`.
        db: Database session dependency.

    Returns:
        dict: 200 with `{records, total, user_id}`.

    Raises:
        UnauthorizedError: If no valid token was supplied (401).
        ForbiddenError: If the caller is not an administrator (403).
        ValidationError: If the status is unknown or the window is invalid (422).
        InternalServerError: If the query fails (500).
    """
    filters: Dict[str, Any] = _history_filters(
        skip, limit, status_filter, start_date, end_date
    )
    return await borrowing_controller.get_all_borrowing_records(
        user_id=user_id, db=db, **filters
    )


@router.get(
    "/overdue-books",
    response_model=List[BorrowRecordResponse],
    status_code=status.HTTP_200_OK,
    summary="List every late loan",
    description=(
        "Admin only. Returns the loans that are late, soonest due date first. "
        "The list covers loans already flagged `OVERDUE` as well as open loans "
        "whose due date has passed but which no scheduled sweep has flagged yet, "
        "so it is correct even before that sweep runs. An empty list is a "
        "successful 200."
    ),
    responses=error_responses(403),
)
async def list_overdue_books(
    _admin: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[BorrowRecordResponse]:
    """Return every late loan.

    Args:
        _admin: The authenticated administrator, resolved by `require_admin`.
        db: Database session dependency.

    Returns:
        list[BorrowRecordResponse]: 200 with the late loans, soonest first.

    Raises:
        UnauthorizedError: If no valid token was supplied (401).
        ForbiddenError: If the caller is not an administrator (403).
        InternalServerError: If the query fails (500).
    """
    return await borrowing_controller.get_overdue_books(db=db)


@router.get(
    "/borrow/{borrowing_record_id}",
    response_model=BorrowRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Read one of the caller's loans",
    description=(
        "Returns a single loan belonging to the authenticated member, so a "
        "client can poll one loan's due date or fine. A loan belonging to "
        "another member is refused with 403 Forbidden. Declared after the two "
        "history paths so `all` is never read as a record id."
    ),
    responses=error_responses(403, 404, 422),
)
async def read_borrowing_record(
    borrowing_record_id: int = Path(
        ..., ge=1, description="Primary key of the loan"
    ),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BorrowRecordResponse:
    """Return one loan owned by the caller.

    Args:
        borrowing_record_id: Primary key of the loan.
        current_user: The authenticated member, resolved by `get_current_user`.
        db: Database session dependency.

    Returns:
        BorrowRecordResponse: 200 with the loan.

    Raises:
        UnauthorizedError: If no valid token was supplied (401).
        NotFoundError: If no such loan exists (404).
        ForbiddenError: If the loan belongs to another member (403).
    """
    return await borrowing_controller.get_borrowing_record(
        user_id=int(current_user["id"]),
        borrowing_record_id=borrowing_record_id,
        db=db,
    )


__all__: list[str] = ["router"]