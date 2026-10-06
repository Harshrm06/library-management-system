"""Book catalog endpoints.

The router is mounted at ``/api/books`` (built from ``settings.api_v1_prefix``
so the mount point stays configurable) and every error raised by the controller
is converted into the ``ErrorResponse`` envelope by the handlers registered in
:mod:`app.main`.

Endpoints:
    * ``GET    /api/books``                       - list, search and paginate
    * ``GET    /api/books/{book_id}``             - read one entry
    * ``POST   /api/books``                       - create an entry (admin)
    * ``PUT    /api/books/{book_id}``             - update an entry (admin)
    * ``DELETE /api/books/{book_id}``             - remove an entry (admin)
    * ``GET    /api/books/{book_id}/availability`` - quick availability check

Read endpoints are public so the catalog can be browsed without an account;
write endpoints depend on :func:`app.middleware.auth_middleware.require_admin`.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.controllers import book_controller
from app.database import get_db
from app.middleware.auth_middleware import require_admin
from app.routes.auth_routes import error_responses
from app.schemas.book_schema import (
    BookAvailabilityResponse,
    BookDeleteResponse,
    BookListResponse,
    BookResponse,
    CreateBookRequest,
    UpdateBookRequest,
)

router = APIRouter(
    prefix=f"{settings.api_v1_prefix}/books",
    tags=["books"],
)

CREATE_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "single_copy": {
                        "summary": "Catalog a new title",
                        "value": {
                            "title": "Dune",
                            "author": "Frank Herbert",
                            "isbn": "978-0-441-01359-3",
                            "genre": "Science fiction",
                            "description": (
                                "A desert planet, a spice, and a very long "
                                "reach of history."
                            ),
                            "published_year": 1965,
                            "total_quantity": 3,
                        },
                    },
                    "copies_already_on_loan": {
                        "summary": "Reconcile inventory during a stock take",
                        "value": {
                            "title": "The Left Hand of Darkness",
                            "author": "Ursula K. Le Guin",
                            "isbn": "9780441478125",
                            "genre": "Science fiction",
                            "total_quantity": 5,
                            "available_quantity": 3,
                        },
                    },
                }
            }
        }
    }
}

UPDATE_REQUEST_EXAMPLE: Dict[str, Any] = {
    "requestBody": {
        "content": {
            "application/json": {
                "examples": {
                    "retitle": {
                        "summary": "Correct the title and author",
                        "value": {
                            "title": "Dune (Deluxe Edition)",
                            "author": "Frank Herbert",
                        },
                    },
                    "inventory": {
                        "summary": "Return a copy, raising availability",
                        "value": {"available_quantity": 3},
                    },
                }
            }
        }
    }
}


@router.get(
    "",
    response_model=BookListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search the catalog",
    description=(
        "Public route. Returns one page of books ordered by `title` by "
        "default. `search` matches title, author or ISBN case-insensitively; "
        "`genre` matches exactly, also case-insensitively. `skip` and `limit` "
        "select the window (`limit` is capped at 100)."
    ),
    responses=error_responses(400, 422),
)
async def list_books(
    skip: int = Query(
        default=0,
        ge=0,
        description="Rows to skip, for offset paging",
    ),
    limit: int = Query(
        default=10,
        ge=1,
        le=100,
        description="Maximum rows to return, 1-100",
    ),
    search: Optional[str] = Query(
        default=None,
        max_length=255,
        description="Case-insensitive match on title, author or ISBN",
        examples=["dune"],
    ),
    genre: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Exact genre filter",
        examples=["Science fiction"],
    ),
    sort_by: str = Query(
        default="title",
        description="Column to sort by, e.g. `title`, `author`, `published_year`",
        examples=["title"],
    ),
    sort_order: str = Query(
        default="asc",
        description="Sort direction, `asc` or `desc`",
        examples=["asc"],
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Return a page of catalog entries.

    Args:
        skip: Rows to skip; must be zero or positive.
        limit: Page size, 1-100; defaults to 10.
        search: Case-insensitive match on title, author or ISBN.
        genre: Exact genre filter.
        sort_by: Column to order by; unknown names fall back to `title`.
        sort_order: `asc` or `desc`.
        db: Database session dependency.

    Returns:
        dict: 200 with `{books, total, page, limit, has_next}`.

    Raises:
        ValidationError: If the pagination window or a filter is invalid (422).
        InternalServerError: If the query fails (500).
    """
    return await book_controller.get_all_books(
        skip=skip,
        limit=limit,
        search=search,
        genre=genre,
        db=db,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    status_code=status.HTTP_200_OK,
    summary="Read one catalog entry",
    description=(
        "Public route. `is_available` is derived from `available_quantity`, so "
        "it is true whenever at least one copy can be borrowed."
    ),
    responses=error_responses(404, 422),
)
async def read_book(
    book_id: int = Path(..., ge=1, description="Primary key of the book"),
    db: Session = Depends(get_db),
) -> BookResponse:
    """Return a single catalog entry.

    Args:
        book_id: Primary key of the book.
        db: Database session dependency.

    Returns:
        BookResponse: 200 with the entry.

    Raises:
        NotFoundError: If no book has that id (404).
    """
    return await book_controller.get_book_by_id(book_id=book_id, db=db)


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a book to the catalog",
    description=(
        "Admin only. Hyphens are stripped from `isbn` and it must be a valid "
        "ISBN-10 or ISBN-13 that no other entry uses. When `available_quantity` "
        "is omitted it is set to `total_quantity`, since a newly catalogued "
        "title normally has every copy on the shelf."
    ),
    responses=error_responses(409, 422),
    openapi_extra=CREATE_REQUEST_EXAMPLE,
)
async def create_book(
    payload: CreateBookRequest,
    _admin: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BookResponse:
    """Create a catalog entry.

    Args:
        payload: Title, author, ISBN and inventory counts.
        _admin: The authenticated administrator, resolved by `require_admin`.
        db: Database session dependency.

    Returns:
        BookResponse: 201 with the created entry.

    Raises:
        ForbiddenError: If the caller is not an administrator (403).
        ConflictError: If the ISBN is already in use (409).
        ValidationError: If the quantities disagree (422).
        InternalServerError: If the insert fails (500).
    """
    return await book_controller.create_book(request=payload, db=db)


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a catalog entry",
    description=(
        "Admin only. Only the fields present in the request body are applied, "
        "so omitted values keep their stored content. Quantities are checked "
        "against the stored values, which means lowering `total_quantity` "
        "below the number of copies currently on loan is rejected."
    ),
    responses=error_responses(404, 409, 422),
    openapi_extra=UPDATE_REQUEST_EXAMPLE,
)
async def update_book(
    payload: UpdateBookRequest,
    book_id: int = Path(..., ge=1, description="Primary key of the book"),
    _admin: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BookResponse:
    """Apply a partial update to a catalog entry.

    Args:
        payload: The fields to change; at least one is required.
        book_id: Primary key of the book.
        _admin: The authenticated administrator, resolved by `require_admin`.
        db: Database session dependency.

    Returns:
        BookResponse: 200 with the updated entry.

    Raises:
        ForbiddenError: If the caller is not an administrator (403).
        NotFoundError: If no book has that id (404).
        ValidationError: If the payload is empty or the quantities disagree (422).
        ConflictError: If a new ISBN is already in use (409).
        InternalServerError: If the update fails (500).
    """
    return await book_controller.update_book(book_id=book_id, request=payload, db=db)


@router.delete(
    "/{book_id}",
    response_model=BookDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a book from the catalog",
    description=(
        "Admin only. Deletion is refused while copies are on loan, because "
        "the loans would lose their target; return every copy first."
    ),
    responses=error_responses(404, 422),
)
async def delete_book(
    book_id: int = Path(..., ge=1, description="Primary key of the book"),
    _admin: Dict[str, Any] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> BookDeleteResponse:
    """Delete a catalog entry.

    Args:
        book_id: Primary key of the book.
        _admin: The authenticated administrator, resolved by `require_admin`.
        db: Database session dependency.

    Returns:
        BookDeleteResponse: 200 with `{success, message, timestamp}`.

    Raises:
        ForbiddenError: If the caller is not an administrator (403).
        NotFoundError: If no book has that id (404).
        ValidationError: If copies are still on loan (422).
        InternalServerError: If the delete fails (500).
    """
    result: Dict[str, Any] = await book_controller.delete_book(book_id=book_id, db=db)
    return BookDeleteResponse(success=True, message=result["message"])


@router.get(
    "/{book_id}/availability",
    response_model=BookAvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Check whether a book can be borrowed",
    description=(
        "Public route. A single row read that answers the question the borrow "
        "flow asks before it starts, so a client does not have to fetch the "
        "whole catalog entry to learn the copy count."
    ),
    responses=error_responses(404, 422),
)
async def read_book_availability(
    book_id: int = Path(..., ge=1, description="Primary key of the book"),
    db: Session = Depends(get_db),
) -> BookAvailabilityResponse:
    """Report the current availability of a book.

    Args:
        book_id: Primary key of the book.
        db: Database session dependency.

    Returns:
        BookAvailabilityResponse: 200 with `{available, quantity, total_quantity,
        title, book_id, timestamp}`.

    Raises:
        NotFoundError: If no book has that id (404).
    """
    book: BookResponse = await book_controller.get_book_by_id(book_id=book_id, db=db)
    return BookAvailabilityResponse(
        book_id=book.id,
        title=book.title,
        available=book.is_available,
        quantity=book.available_quantity,
        total_quantity=book.total_quantity,
    )


__all__: list[str] = ["router"]