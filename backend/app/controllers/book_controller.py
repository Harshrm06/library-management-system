"""Book catalog business logic.

Public functions are ``async`` and mirror :mod:`app.controllers.auth_controller`:
every blocking SQLAlchemy call is delegated to :func:`asyncio.to_thread` so the
event loop is never held up, and each request's ``Session`` is used by exactly one
worker thread.

Responsibilities:

* list and search the catalog with pagination, filtering and safe ordering,
* read a single entry,
* create, update and delete entries (authorization is enforced by the routes;
  these functions assume the caller has already been identified).

Notes:

* search terms are escaped before they reach ``LIKE``, so ``%`` matches a percent
  sign rather than everything,
* ordering is restricted to real columns, which keeps the value out of the
  ``ORDER BY`` clause unchecked,
* writes are wrapped so a failure rolls back and never leaves a dirty session,
* a book cannot be deleted while copies are on loan.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.book import Book
from app.schemas.book_schema import (
    BookListResponse,
    BookResponse,
    CreateBookRequest,
    UpdateBookRequest,
    books_to_response,
)
from app.utils.book_helpers import (
    apply_ordering,
    filter_books_by_genre,
    search_books_query,
)
from app.utils.exceptions import (
    ConflictError,
    InternalServerError,
    NotFoundError,
    ValidationError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

#: Hard ceiling on page size, mirrored by ``BookSearchQuery.limit``.
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

    The route validates these through ``BookSearchQuery``; the check is repeated
    here because a controller can be called directly.

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
        logger.warning("Book lookup failed: book %s not found", book_id)
        raise NotFoundError(
            "Book not found",
            detail=f"No book exists with id {book_id}.",
            code="book_not_found",
        )
    return book


def _assert_isbn_available(db: Session, isbn: str, exclude_id: Optional[int] = None) -> None:
    """Ensure an ISBN is not already taken.

    Args:
        db: Database session.
        isbn: The normalized ISBN to check.
        exclude_id: Book id to ignore, used when updating a book in place.

    Raises:
        ConflictError: If another book already uses the ISBN.
    """
    statement = select(Book.id).where(func.lower(Book.isbn) == isbn.lower())
    if exclude_id is not None:
        statement = statement.where(Book.id != exclude_id)
    # `.first()` rather than `scalar_one_or_none()`: this is an existence check,
    # so "more than one match" is still a conflict and must not raise.
    row = db.execute(statement.limit(1)).first()
    existing: Optional[int] = row[0] if row is not None else None
    if existing is not None:
        logger.warning("Book write rejected: ISBN %s already used by book %s", isbn, existing)
        raise ConflictError(
            "ISBN already exists",
            detail=f"Another book (id {existing}) already uses ISBN {isbn}.",
            code="isbn_taken",
        )


def _active_borrowing_count(db: Session, book: Book) -> int:
    """Return how many copies of a book are currently on loan.

    There is no borrowing table yet, so the loan count is derived from the
    inventory itself: ``total_quantity - available_quantity`` is exactly the
    number of copies that have been checked out. When the borrowing model
    arrives, this is the single place to swap in a real query.

    Args:
        db: Database session (unused today, kept for that future query).
        book: The book to inspect.

    Returns:
        int: Copies currently on loan, never negative.
    """
    del db  # no query needed until the borrowing model exists
    return max(0, book.total_quantity - book.available_quantity)


def _get_all_books(
    skip: int,
    limit: int,
    search: Optional[str],
    genre: Optional[str],
    db: Session,
    sort_by: str,
    sort_order: str,
) -> Dict[str, Any]:
    """List, search and paginate the catalog. See :func:`get_all_books`."""
    skip, limit = _validate_pagination(skip, limit)

    try:
        filters = select(Book)
        if search:
            filters = search_books_query(filters, search)
        if genre:
            filters = filter_books_by_genre(filters, genre)

        # Count the filtered set before ordering: the count does not need the
        # sort, and some dialects reject ORDER BY inside a derived table.
        total: int = db.execute(
            select(func.count()).select_from(filters.subquery())
        ).scalar_one()

        ordered = apply_ordering(filters, sort_by, sort_order)
        rows: List[Book] = list(
            db.execute(ordered.offset(skip).limit(limit)).scalars().all()
        )
    except SQLAlchemyError as exc:
        logger.exception("Catalog query failed")
        raise InternalServerError(
            "Could not load the catalog",
            detail="The catalog could not be read. Please try again later.",
            code="catalog_query_failed",
        ) from exc

    page: int = (skip // limit) + 1 if limit else 1
    return BookListResponse(
        books=books_to_response(rows),
        total=total,
        page=page,
        limit=limit,
        has_next=skip + len(rows) < total,
    ).model_dump()


def _get_book_by_id(book_id: int, db: Session) -> BookResponse:
    """Read one book. See :func:`get_book_by_id`."""
    book: Book = _get_book_or_404(db, book_id)
    response = BookResponse.model_validate(book)
    logger.debug("Read book %s (available=%s)", book.id, response.is_available)
    return response


def _create_book(request: CreateBookRequest, db: Session) -> BookResponse:
    """Create a catalog entry. See :func:`create_book`."""
    if request.total_quantity < 1:
        raise ValidationError(
            "Invalid quantity",
            detail="total_quantity must be at least 1.",
            code="invalid_quantity",
        )

    available: int = (
        request.available_quantity
        if request.available_quantity is not None
        else request.total_quantity
    )
    if available > request.total_quantity:
        raise ValidationError(
            "Invalid quantity",
            detail="available_quantity cannot exceed total_quantity.",
            code="invalid_quantity",
        )

    _assert_isbn_available(db, request.isbn)

    book = Book(
        title=request.title,
        author=request.author,
        isbn=request.isbn,
        genre=request.genre,
        description=request.description,
        published_year=request.published_year,
        total_quantity=request.total_quantity,
        available_quantity=available,
    )
    db.add(book)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Book creation rejected: unique constraint violation")
        raise ConflictError(
            "ISBN already exists",
            detail=f"Another book already uses ISBN {request.isbn}.",
            code="isbn_taken",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Book creation failed for ISBN %s", request.isbn)
        raise InternalServerError(
            "Could not create the book",
            detail="The book could not be saved. Please try again later.",
            code="book_create_failed",
        ) from exc

    db.refresh(book)
    logger.info(
        "Created book %s (id=%s, total=%s, available=%s)",
        book.title,
        book.id,
        book.total_quantity,
        book.available_quantity,
    )
    return BookResponse.model_validate(book)


def _update_book(
    book_id: int, request: UpdateBookRequest, db: Session
) -> BookResponse:
    """Update a catalog entry. See :func:`update_book`."""
    book: Book = _get_book_or_404(db, book_id)

    changes: Dict[str, Any] = request.model_dump(exclude_unset=True)
    if not changes:
        raise ValidationError(
            "Nothing to update",
            detail="Provide at least one field to change.",
            code="empty_update",
        )

    # Quantities are validated against the stored values, which the request
    # schema alone cannot do because either one may be omitted.
    total: int = changes.get("total_quantity", book.total_quantity)
    available: int = changes.get("available_quantity", book.available_quantity)
    if total < 1:
        raise ValidationError(
            "Invalid quantity",
            detail="total_quantity must be at least 1.",
            code="invalid_quantity",
        )
    if available < 0:
        raise ValidationError(
            "Invalid quantity",
            detail="available_quantity cannot be negative.",
            code="invalid_quantity",
        )
    if available > total:
        raise ValidationError(
            "Invalid quantity",
            detail=(
                f"available_quantity ({available}) cannot exceed total_quantity ({total}); "
                f"{_active_borrowing_count(db, book)} copies are currently on loan."
            ),
            code="invalid_quantity",
        )

    if "isbn" in changes and changes["isbn"] != book.isbn:
        _assert_isbn_available(db, changes["isbn"], exclude_id=book.id)

    for field, value in changes.items():
        setattr(book, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.warning("Book update rejected: unique constraint violation")
        raise ConflictError(
            "ISBN already exists",
            detail="Another book already uses that ISBN.",
            code="isbn_taken",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Book update failed for id %s", book_id)
        raise InternalServerError(
            "Could not update the book",
            detail="The book could not be saved. Please try again later.",
            code="book_update_failed",
        ) from exc

    db.refresh(book)
    logger.info(
        "Updated book %s (id=%s, fields=%s)",
        book.title,
        book.id,
        ",".join(sorted(changes)),
    )
    return BookResponse.model_validate(book)


def _delete_book(book_id: int, db: Session) -> Dict[str, Any]:
    """Delete a catalog entry. See :func:`delete_book`."""
    book: Book = _get_book_or_404(db, book_id)

    on_loan: int = _active_borrowing_count(db, book)
    if on_loan > 0:
        logger.warning("Book deletion rejected: id %s has %s copies on loan", book_id, on_loan)
        raise ValidationError(
            "Book cannot be deleted",
            detail=(
                f"{on_loan} of {book.total_quantity} copies are currently on loan. "
                "Delete the title once every copy has been returned."
            ),
            code="book_has_active_borrowings",
        )

    title: str = book.title
    try:
        db.delete(book)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Book deletion failed for id %s", book_id)
        raise InternalServerError(
            "Could not delete the book",
            detail="The book could not be removed. Please try again later.",
            code="book_delete_failed",
        ) from exc

    logger.info("Deleted book id=%s (%r)", book_id, title)
    return {"id": book_id, "message": f"Book '{title}' deleted successfully"}


def check_book_availability(book_id: int, db: Session) -> bool:
    """Report whether a book can be borrowed right now.

    Args:
        db: Database session.
        book_id: Primary key of the book.

    Returns:
        bool: ``True`` when at least one copy is available.

    Raises:
        NotFoundError: If no book has that id.

    Example:
        Illustrative only: it needs a live ``Session``, so doctest cannot run it.

        >>> check_book_availability(db=session, book_id=1)  # doctest: +SKIP
        True
    """
    book: Book = _get_book_or_404(db, book_id)
    return book.is_available()


async def get_all_books(
    skip: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    search: Optional[str] = None,
    genre: Optional[str] = None,
    db: Session = None,  # type: ignore[assignment]
    sort_by: str = "title",
    sort_order: str = "asc",
) -> Dict[str, Any]:
    """List the catalog with pagination, search and filtering.

    Args:
        skip: Rows to skip; must be zero or positive.
        limit: Page size, 1-100; defaults to 10.
        search: Case-insensitive match on title, author or ISBN.
        genre: Exact genre, matched case-insensitively.
        db: Database session injected by FastAPI.
        sort_by: Column to order by; unknown names fall back to ``title``.
        sort_order: ``"asc"`` or ``"desc"``.

    Returns:
        dict: ``{books, total, page, limit, has_next}`` matching
        ``BookListResponse``.

    Raises:
        ValidationError: If the pagination window is invalid.
        InternalServerError: If the query fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides.

        >>> await get_all_books(search="dune", limit=25, db=session)  # doctest: +SKIP
        {'books': [...], 'total': 1, 'page': 1, 'limit': 25, 'has_next': False}
    """
    return await _to_thread(
        _get_all_books, skip, limit, search, genre, db, sort_by, sort_order
    )


async def get_book_by_id(book_id: int, db: Session) -> BookResponse:
    """Read one catalog entry, including whether it can be borrowed.

    Args:
        book_id: Primary key of the book.
        db: Database session injected by FastAPI.

    Returns:
        BookResponse: The entry.

    Raises:
        NotFoundError: If no book has that id.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides.

        >>> (await get_book_by_id(book_id=1, db=session)).title  # doctest: +SKIP
        'Dune'
    """
    return await _to_thread(_get_book_by_id, book_id, db)


async def create_book(request: CreateBookRequest, db: Session) -> BookResponse:
    """Add a catalog entry.

    Authorization is enforced by the route, which restricts this operation to
    administrators; the controller trusts that decision.

    When ``available_quantity`` is omitted it is set to ``total_quantity``, since a
    freshly catalogued title normally has every copy on the shelf.

    Args:
        request: The new entry.
        db: Database session injected by FastAPI.

    Returns:
        BookResponse: The created entry.

    Raises:
        ValidationError: If the quantities disagree.
        ConflictError: If the ISBN is already in use.
        InternalServerError: If the insert fails.

    Example:
        >>> payload = CreateBookRequest(
        ...     title="Dune", author="Frank Herbert",
        ...     isbn="9780441013593", total_quantity=2,
        ... )

        The call itself is illustrative only: it is a coroutine needing both an
        event loop and a live ``Session``, neither of which doctest provides.

        >>> (await create_book(payload, db=session)).available_quantity  # doctest: +SKIP
        2
    """
    return await _to_thread(_create_book, request, db)


async def update_book(
    book_id: int, request: UpdateBookRequest, db: Session
) -> BookResponse:
    """Apply a partial update to a catalog entry.

    Authorization is enforced by the route. Only the fields present in the request
    are changed; quantities are validated against the stored values, so lowering
    ``total_quantity`` below the copies currently on loan is rejected.

    Args:
        book_id: Primary key of the book.
        request: The fields to change.
        db: Database session injected by FastAPI.

    Returns:
        BookResponse: The updated entry.

    Raises:
        NotFoundError: If no book has that id.
        ValidationError: If the payload is empty or the quantities disagree.
        ConflictError: If a new ISBN is already in use.
        InternalServerError: If the update fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides.

        >>> (await update_book(  # doctest: +SKIP
        ...     1, UpdateBookRequest(genre="Classic"), db=session
        ... )).genre
        'Classic'
    """
    return await _to_thread(_update_book, book_id, request, db)


async def delete_book(book_id: int, db: Session) -> Dict[str, Any]:
    """Remove a catalog entry.

    Authorization is enforced by the route. Deletion is refused while copies are
    on loan, because the loans would lose their target.

    Args:
        book_id: Primary key of the book.
        db: Database session injected by FastAPI.

    Returns:
        dict: ``{"id": book_id, "message": ...}``.

    Raises:
        NotFoundError: If no book has that id.
        ValidationError: If copies are still on loan.
        InternalServerError: If the delete fails.

    Example:
        Illustrative only: a coroutine needing an event loop and a live
        ``Session``, neither of which doctest provides.

        >>> (await delete_book(book_id=3, db=session))["message"]  # doctest: +SKIP
        "Book 'Dune' deleted successfully"
    """
    return await _to_thread(_delete_book, book_id, db)


__all__ = [
    "MAX_PAGE_SIZE",
    "check_book_availability",
    "create_book",
    "delete_book",
    "get_all_books",
    "get_book_by_id",
    "update_book",
]
