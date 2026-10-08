"""Pydantic schemas for the book catalog.

The module groups the request and response models used by the book endpoints:

* :class:`BookBaseSchema` - the descriptive fields shared by every payload;
* :class:`CreateBookRequest` - a full catalog entry with its inventory;
* :class:`UpdateBookRequest` - a partial update, every field optional;
* :class:`BookResponse` and :class:`BookListResponse` - what the API returns;
* :class:`BookSearchQuery` - pagination, filtering and sorting.

Validation rules live in :mod:`app.utils.validators` so the controllers can
reuse them, and every field carries ``examples`` so ``/docs`` shows realistic
payloads.

Example:
    >>> CreateBookRequest(
    ...     title="Dune",
    ...     author="Frank Herbert",
    ...     isbn="9780441013593",
    ...     total_quantity=3,
    ...     available_quantity=3,
    ... ).total_quantity
    3
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.utils.validators import validate_isbn_format

#: Columns a caller may sort by. Kept closed so the value can never be
#: interpolated into an ORDER BY clause unchecked.
SORTABLE_FIELDS: frozenset[str] = frozenset(
    {"title", "author", "genre", "published_year", "available_quantity", "created_at"}
)


def _strip(value: Optional[str]) -> Optional[str]:
    """Normalize an optional text field.

    Args:
        value: The raw value, possibly ``None`` or padded with whitespace.

    Returns:
        str | None: The trimmed value, or ``None`` when it is blank.
    """
    if value is None:
        return None
    candidate: str = value.strip()
    return candidate or None


class BookBaseSchema(BaseModel):
    """Descriptive fields every book payload shares.

    Used as the base for administrative create/update payloads. Text is trimmed
    on the way in, and blank optional fields collapse to ``None`` so the catalog
    does not accumulate empty strings.
    """

    title: str = Field(
        min_length=1,
        max_length=255,
        description="Book title as printed on the cover",
        examples=["Dune"],
    )
    author: str = Field(
        min_length=1,
        max_length=255,
        description="Primary author",
        examples=["Frank Herbert"],
    )
    isbn: str = Field(
        min_length=10,
        max_length=20,
        description="Unique 10 or 13 digit ISBN; hyphens are accepted and stripped",
        examples=["978-0-441-01359-3"],
    )
    genre: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Optional genre used for catalog filtering",
        examples=["Science fiction"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional synopsis",
        examples=["A desert planet, a spice, and a very long reach of history."],
    )
    published_year: Optional[int] = Field(
        default=None,
        ge=0,
        le=3000,
        description="Optional year of first publication",
        examples=[1965],
    )

    @field_validator("title", "author")
    @classmethod
    def _validate_required_text(cls, value: str) -> str:
        """Reject text that is only whitespace.

        Args:
            value: The field value.

        Returns:
            str: The trimmed value.

        Raises:
            ValueError: If nothing is left after trimming.
        """
        candidate: str = value.strip()
        if not candidate:
            raise ValueError("Value cannot be blank")
        return candidate

    @field_validator("genre", "description", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> Optional[str]:
        """Trim optional text and treat blanks as missing.

        Args:
            value: The raw field value.

        Returns:
            str | None: The trimmed value, or ``None``.
        """
        return _strip(value if isinstance(value, str) else value)

    @field_validator("isbn")
    @classmethod
    def _validate_isbn(cls, value: str) -> str:
        """Normalize and check the ISBN.

        Args:
            value: The ISBN supplied by the client, hyphens allowed.

        Returns:
            str: The digits (and a trailing ``X`` for ISBN-10) in upper case.

        Raises:
            ValueError: If the value is not a valid ISBN-10 or ISBN-13.
        """
        if not validate_isbn_format(value):
            raise ValueError("ISBN must be a valid 10 or 13 digit ISBN")
        return value.strip().replace("-", "").upper()


class CreateBookRequest(BookBaseSchema):
    """Payload for ``POST /api/books`` (admin only).

    ``total_quantity`` is how many copies the library owns. ``available_quantity``
    is how many are not on loan and may be omitted, in which case every copy is
    considered available - the usual case when a title is first catalogued.

    Example:
        >>> payload = CreateBookRequest(
        ...     title="Dune",
        ...     author="Frank Herbert",
        ...     isbn="9780441013593",
        ...     total_quantity=3,
        ... )
        >>> payload.available_quantity is None
        True
    """

    model_config = ConfigDict(extra="forbid")

    total_quantity: int = Field(
        ge=1,
        le=100000,
        description="Copies owned by the library; must be at least 1",
        examples=[3],
    )
    available_quantity: Optional[int] = Field(
        default=None,
        ge=0,
        le=100000,
        description="Copies not on loan; defaults to total_quantity",
        examples=[3],
    )

    @model_validator(mode="after")
    def _validate_quantities(self) -> "CreateBookRequest":
        """Ensure the inventory numbers agree with each other.

        Returns:
            CreateBookRequest: The validated payload.

        Raises:
            ValueError: If ``available_quantity`` exceeds ``total_quantity``.
        """
        if (
            self.available_quantity is not None
            and self.available_quantity > self.total_quantity
        ):
            raise ValueError("available_quantity cannot exceed total_quantity")
        return self


class UpdateBookRequest(BaseModel):
    """Payload for ``PUT /api/books/{id}`` (admin only).

    Every field is optional; only the fields the client actually sends are
    applied, so omitted values keep their stored content. ``isbn`` may not be
    changed once copies are on loan, so the API keeps it immutable in practice -
    the field exists here to validate the format if it is ever sent.

    Example:
        >>> UpdateBookRequest(available_quantity=2).model_dump(exclude_unset=True)
        {'available_quantity': 2}
    """

    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(
        default=None, min_length=1, max_length=255, description="New title"
    )
    author: Optional[str] = Field(
        default=None, min_length=1, max_length=255, description="New primary author"
    )
    isbn: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=20,
        description="New ISBN, validated but rarely changed",
    )
    genre: Optional[str] = Field(
        default=None, max_length=100, description="New genre"
    )
    description: Optional[str] = Field(default=None, description="New synopsis")
    total_quantity: Optional[int] = Field(
        default=None, ge=1, le=100000, description="New number of owned copies"
    )
    available_quantity: Optional[int] = Field(
        default=None, ge=0, le=100000, description="New number of copies not on loan"
    )
    published_year: Optional[int] = Field(
        default=None, ge=0, le=3000, description="New year of first publication"
    )

    @field_validator("title", "author")
    @classmethod
    def _validate_required_text(cls, value: Optional[str]) -> Optional[str]:
        """Reject text that is only whitespace.

        Args:
            value: The field value, or ``None`` to leave it unchanged.

        Returns:
            str | None: The trimmed value.

        Raises:
            ValueError: If a supplied value is blank.
        """
        if value is None:
            return None
        candidate: str = value.strip()
        if not candidate:
            raise ValueError("Value cannot be blank")
        return candidate

    @field_validator("genre", "description", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: Any) -> Optional[str]:
        """Trim optional text and turn blanks into explicit ``None``.

        Args:
            value: The raw field value.

        Returns:
            str | None: The trimmed value, or ``None``.
        """
        return _strip(value if isinstance(value, str) else value)

    @field_validator("isbn")
    @classmethod
    def _validate_isbn(cls, value: Optional[str]) -> Optional[str]:
        """Normalize and check the ISBN when one is supplied.

        Args:
            value: The ISBN, or ``None`` to leave it unchanged.

        Returns:
            str | None: The digits in upper case.

        Raises:
            ValueError: If the value is not a valid ISBN-10 or ISBN-13.
        """
        if value is None:
            return None
        if not validate_isbn_format(value):
            raise ValueError("ISBN must be a valid 10 or 13 digit ISBN")
        return value.strip().replace("-", "").upper()

    @model_validator(mode="after")
    def _validate_quantities(self) -> "UpdateBookRequest":
        """Reject an update that would lend more copies than are owned.

        A partial update is validated against the stored values by the
        controller; this check catches the case where both quantities are sent
        together and disagree.

        Returns:
            UpdateBookRequest: The validated payload.

        Raises:
            ValueError: If ``available_quantity`` exceeds ``total_quantity``.
        """
        if (
            self.total_quantity is not None
            and self.available_quantity is not None
            and self.available_quantity > self.total_quantity
        ):
            raise ValueError("available_quantity cannot exceed total_quantity")
        return self


class BookResponse(BaseModel):
    """Public representation of a catalog entry.

    ``model_config`` enables ``from_attributes`` so the ORM row can be validated
    directly::

        BookResponse.model_validate(book_row)

    ``is_available`` is derived from ``available_quantity`` instead of being read
    off the row, because the model exposes availability as the method
    ``Book.is_available()`` rather than as an attribute - reading the attribute
    would hand pydantic a bound method and fail validation.

    Example:
        >>> BookResponse.model_validate(book_row).is_available  # doctest: +SKIP
        True
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Primary key of the book", examples=[1])
    title: str = Field(description="Book title", examples=["Dune"])
    author: str = Field(description="Primary author", examples=["Frank Herbert"])
    isbn: str = Field(description="Normalized ISBN digits", examples=["9780441013593"])
    genre: Optional[str] = Field(default=None, description="Genre", examples=["Science fiction"])
    description: Optional[str] = Field(default=None, description="Synopsis")
    total_quantity: int = Field(description="Copies owned", examples=[3])
    available_quantity: int = Field(description="Copies not on loan", examples=[2])
    published_year: Optional[int] = Field(default=None, description="Year of publication")
    is_available: bool = Field(
        default=False, description="True when at least one copy can be borrowed"
    )
    created_at: datetime = Field(description="UTC creation timestamp")
    updated_at: Optional[datetime] = Field(
        default=None,
        description="UTC timestamp of the last edit; null for rows written before it was tracked",
    )

    @model_validator(mode="before")
    @classmethod
    def _accept_rows_and_dicts(cls, data: Any) -> Any:
        """Normalize an ORM row into field values plus derived availability.

        Args:
            data: A ``Book`` instance, a mapping, or anything with the matching
                attributes.

        Returns:
            dict | Any: A mapping of field names to values, or ``data``
            unchanged when it is already a mapping.
        """
        if isinstance(data, dict):
            return data

        values: Dict[str, Any] = {}
        for name in cls.model_fields:
            # Skip callables such as `Book.is_available()`, which are methods and
            # not stored values.
            if name == "is_available":
                continue
            attribute = getattr(data, name, None)
            if attribute is None or not callable(attribute):
                values[name] = attribute

        available = getattr(data, "available_quantity", 0) or 0
        values["is_available"] = available > 0
        return values


class BookListResponse(BaseModel):
    """One page of catalog results supporting dual schema conventions."""

    model_config = ConfigDict(from_attributes=True)

    items: List[BookResponse] = Field(default_factory=list, description="Books on this page")
    books: List[BookResponse] = Field(default_factory=list, description="Books on this page (alias)")
    total: int = Field(ge=0, default=0, description="Total books matching query")
    page: int = Field(ge=1, default=1, description="1-based page number")
    page_size: int = Field(ge=1, le=100, default=10, description="Page size")
    limit: int = Field(ge=1, le=100, default=10, description="Page size (alias)")
    has_next: bool = Field(default=False, description="True when another page follows")

    @model_validator(mode="before")
    @classmethod
    def _normalize_pagination(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "items" in data and "books" not in data:
                data["books"] = data["items"]
            elif "books" in data and "items" not in data:
                data["items"] = data["books"]

            if "page_size" in data and "limit" not in data:
                data["limit"] = data["page_size"]
            elif "limit" in data and "page_size" not in data:
                data["page_size"] = data["limit"]

            if "has_next" not in data:
                page = data.get("page", 1)
                size = data.get("page_size", data.get("limit", 10))
                total = data.get("total", 0)
                data["has_next"] = (page * size) < total
        return data


class BookSearchQuery(BaseModel):
    """Query parameters for ``GET /api/books``.

    ``skip``/``limit`` describe the window, ``search`` matches title, author or
    ISBN, ``genre`` filters exactly, and ``sort_by`` names the column to order by.
    Sorting is restricted to :data:`SORTABLE_FIELDS` because the value ends up in
    an ORDER BY clause.

    Example:
        >>> BookSearchQuery(search="dune", limit=25).sort_by
        'title'
    """

    model_config = ConfigDict(extra="forbid")

    skip: int = Field(default=0, ge=0, description="Rows to skip, for offset paging")
    limit: int = Field(
        default=10, ge=1, le=100, description="Maximum rows to return, 1-100"
    )
    search: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Case-insensitive match on title, author or ISBN",
        examples=["dune"],
    )
    genre: Optional[str] = Field(
        default=None, max_length=100, description="Exact genre filter", examples=["Science fiction"]
    )
    sort_by: str = Field(
        default="title",
        description=f"Column to sort by; one of {', '.join(sorted(SORTABLE_FIELDS))}",
        examples=["title"],
    )
    sort_order: str = Field(
        default="asc", description="Sort direction, `asc` or `desc`", examples=["asc"]
    )

    @field_validator("search", "genre", mode="before")
    @classmethod
    def _normalize_query_text(cls, value: Any) -> Optional[str]:
        """Trim filters and treat blanks as absent.

        Args:
            value: The raw query value.

        Returns:
            str | None: The trimmed value, or ``None``.
        """
        return _strip(value if isinstance(value, str) else value)

    @field_validator("sort_by")
    @classmethod
    def _validate_sort_by(cls, value: str) -> str:
        """Restrict sorting to known columns.

        Args:
            value: The requested column.

        Returns:
            str: The lowercase column name.

        Raises:
            ValueError: If the column is not sortable.
        """
        candidate: str = value.strip().lower()
        if candidate not in SORTABLE_FIELDS:
            raise ValueError(
                f"sort_by must be one of: {', '.join(sorted(SORTABLE_FIELDS))}"
            )
        return candidate

    @field_validator("sort_order")
    @classmethod
    def _validate_sort_order(cls, value: str) -> str:
        """Restrict the sort direction to ``asc`` or ``desc``.

        Args:
            value: The requested direction.

        Returns:
            str: The lowercase direction.

        Raises:
            ValueError: If the direction is neither ``asc`` nor ``desc``.
        """
        candidate: str = value.strip().lower()
        if candidate not in {"asc", "desc"}:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return candidate

    def order_by_clause(self) -> str:
        """Return the SQL expression for this query's sort order.

        The column name is validated by :data:`SORTABLE_FIELDS`, so the result is
        safe to interpolate into ``ORDER BY``; a direction that is not
        ``asc``/``desc`` is rejected too.

        Returns:
            str: For example ``title asc``.

        Example:
            >>> BookSearchQuery(sort_by="author", sort_order="desc").order_by_clause()
            'author desc'
        """
        column: str = self.sort_by.lower()
        direction: str = "desc" if self.sort_order.lower() == "desc" else "asc"
        return f"{column} {direction}"


class BookAvailabilityResponse(BaseModel):
    """Result of ``GET /api/books/{id}/availability``.

    Carries both the boolean the caller most often needs and the raw copy count
    so a client can show "3 of 5 copies available" without a second request.

    Example:
        >>> BookAvailabilityResponse(
        ...     book_id=7, title="Dune", available=True, quantity=3, total_quantity=5
        ... ).model_dump()["quantity"]
        3
    """

    book_id: int = Field(description="Primary key of the book", examples=[1])
    title: str = Field(description="Book title", examples=["Dune"])
    available: bool = Field(description="True when at least one copy can be borrowed")
    quantity: int = Field(ge=0, description="Copies currently not on loan", examples=[2])
    total_quantity: int = Field(ge=1, description="Copies owned", examples=[3])
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Server time of the response",
    )


class BookDeleteResponse(BaseModel):
    """Envelope returned by ``DELETE /api/books/{id}``.

    Example:
        >>> BookDeleteResponse(message="Book 'Dune' deleted successfully").success
        True
    """

    success: bool = Field(default=True, description="Always true on success")
    message: str = Field(
        description="Human readable outcome",
        examples=["Book 'Dune' deleted successfully"],
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Server time of the response",
    )


def books_to_response(rows: List[Any]) -> List[BookResponse]:
    """Convert ORM rows into response models.

    Args:
        rows: ``Book`` instances, or anything with the matching attributes.

    Returns:
        list[BookResponse]: One response per row, in the same order.

    Example:
        >>> books_to_response([book_row])[0].id  # doctest: +SKIP
        1
    """
    return [BookResponse.model_validate(row) for row in rows]


BookCreate = CreateBookRequest
BookUpdate = UpdateBookRequest
BookOut = BookResponse

__all__: List[str] = [
    "SORTABLE_FIELDS",
    "BookAvailabilityResponse",
    "BookBaseSchema",
    "BookCreate",
    "BookDeleteResponse",
    "BookListResponse",
    "BookOut",
    "BookResponse",
    "BookSearchQuery",
    "BookUpdate",
    "CreateBookRequest",
    "UpdateBookRequest",
    "books_to_response",
]
