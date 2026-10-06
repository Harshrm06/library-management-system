"""Query helpers for the book catalog.

These are pure SQLAlchemy builders: they take a ``Select`` and return a filtered
``Select`` without touching the database, so they are cheap to unit test and can
be composed in any order. ``app.controllers.book_controller`` uses them to build
the catalog listing.

Example:
    >>> statement = search_books_query(select(Book), "dune")
    >>> str(statement).count("lower")  # doctest: +SKIP
    3
"""

from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import Select, func, or_, select

from app.models.book import Book
from app.utils.validators import validate_isbn_format

# Any ``Select`` subtype can be filtered, so the helpers stay generic.
S = TypeVar("S", bound=Select[Any])


def validate_isbn(isbn: str) -> bool:
    """Check that a value is a plausible ISBN.

    Thin wrapper over :func:`app.utils.validators.validate_isbn_format` so
    catalog code has a single obvious entry point.

    Args:
        isbn: The identifier to check.

    Returns:
        bool: ``True`` for a 10 digit ISBN (trailing ``X`` allowed) or a 13 digit
        one, with hyphens and spaces permitted.

    Example:
        >>> validate_isbn("978-0-441-01359-3")
        True
        >>> validate_isbn("12345")
        False
    """
    return validate_isbn_format(isbn)


def escape_like(term: str) -> str:
    """Escape the wildcard characters of a LIKE pattern.

    Without this, a search for ``100%`` would match every title, and ``_`` would
    match any single character.

    Args:
        term: The raw user supplied search text.

    Returns:
        str: The text with ``%``, ``_`` and the escape character itself escaped.

    Example:
        >>> escape_like("50%_off")
        '50\\\\%\\\\_off'
    """
    escaped: str = (
        term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return escaped


def search_books_query(db_query: S, search: str) -> S:
    """Match title, author or ISBN, case-insensitively.

    Args:
        db_query: The statement to filter.
        search: Free text; blank input leaves the statement untouched.

    Returns:
        The filtered statement, with ``ILIKE`` used when the dialect supports it
        and ``LIKE`` on ``lower(...)`` otherwise (MySQL).

    Example:
        >>> search_books_query(select(Book), "herbert") is not None
        True
    """
    if not isinstance(search, str) or not search.strip():
        return db_query

    pattern: str = f"%{escape_like(search.strip().lower())}%"
    conditions = (
        func.lower(Book.title).like(pattern, escape="\\"),
        func.lower(Book.author).like(pattern, escape="\\"),
        func.lower(Book.isbn).like(pattern, escape="\\"),
    )
    return db_query.where(or_(*conditions))


def filter_books_by_genre(db_query: S, genre: str) -> S:
    """Restrict a statement to one genre, case-insensitively.

    Args:
        db_query: The statement to filter.
        genre: Genre name; blank input leaves the statement untouched.

    Returns:
        The filtered statement.

    Example:
        >>> filter_books_by_genre(select(Book), "Science fiction") is not None
        True
    """
    if not isinstance(genre, str) or not genre.strip():
        return db_query
    return db_query.where(func.lower(Book.genre) == genre.strip().lower())


def apply_ordering(
    db_query: S, sort_by: str = "title", sort_order: str = "asc"
) -> S:
    """Order a statement by an allow-listed column.

    The column name is checked against the model's own columns before it is
    handed to SQLAlchemy, so a crafted value can never reach ``ORDER BY``.

    Args:
        db_query: The statement to order.
        sort_by: Column name; unknown names fall back to ``title``.
        sort_order: ``"asc"`` or ``"desc"``; anything else falls back to ``asc``.

    Returns:
        The ordered statement.

    Example:
        >>> str(apply_ordering(select(Book), "author", "asc")).endswith("books.author ASC")
        True
    """
    columns = Book.__table__.columns
    column_name: str = sort_by.strip().lower() if isinstance(sort_by, str) else "title"
    if column_name not in columns:
        column_name = "title"
    descending: bool = isinstance(sort_order, str) and sort_order.strip().lower() == "desc"
    return db_query.order_by(columns[column_name].desc() if descending else columns[column_name].asc())


__all__ = [
    "apply_ordering",
    "escape_like",
    "filter_books_by_genre",
    "search_books_query",
    "validate_isbn",
]
