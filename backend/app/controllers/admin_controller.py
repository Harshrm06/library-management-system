"""Admin business logic for dashboard statistics, user management, book inventory management, and admin borrowing history."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole
from app.schemas.book_schema import (
    BookCreate,
    BookListResponse,
    BookOut,
    BookUpdate,
)
from app.schemas.borrowing_schema import (
    AdminBorrowingHistoryItem,
    AdminBorrowingHistoryResponse,
    DashboardStatisticsSchema,
)
from app.schemas.user_schema import UserListResponse, UserOut, UserRoleUpdate
from app.utils.exceptions import BadRequestError, ConflictError, NotFoundError


def _parse_date_param(
    val: Optional[str | datetime | date], param_name: str, is_end_of_day: bool = False
) -> Optional[datetime]:
    """Helper to parse optional date/timestamp parameter.

    Args:
        val: Input date value (str, date, or datetime).
        param_name: Name of parameter for error messaging.
        is_end_of_day: If True and input is date only, set time to 23:59:59.999999.

    Returns:
        Optional[datetime]: Parsed datetime object or None.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        if is_end_of_day:
            return datetime.combine(val, time.max)
        return datetime.combine(val, time.min)
    if isinstance(val, str):
        v = val.strip()
        if not v:
            return None
        try:
            dt = datetime.fromisoformat(v)
            if is_end_of_day and len(v) <= 10:
                return datetime.combine(dt.date(), time.max)
            return dt
        except ValueError:
            raise BadRequestError(
                f"Invalid {param_name} format: '{val}'. Expected YYYY-MM-DD or ISO timestamp.",
                code="invalid_date_format",
            )
    return None


def get_dashboard_statistics(db: Session) -> DashboardStatisticsSchema:
    """Compute aggregate library statistics for the admin dashboard.

    Args:
        db: Active database session.

    Returns:
        DashboardStatisticsSchema: Aggregate metrics computed using database queries.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    total_books: int = db.execute(select(func.count(Book.id))).scalar() or 0

    available_books: int = db.execute(
        select(func.count(Book.id)).where(Book.available_quantity > 0)
    ).scalar() or 0

    sums = db.execute(
        select(
            func.coalesce(func.sum(Book.total_quantity), 0),
            func.coalesce(func.sum(Book.available_quantity), 0),
        )
    ).one()
    total_copies: int = int(sums[0])
    available_copies: int = int(sums[1])

    total_members: int = db.execute(
        select(func.count(User.id)).where(User.role == UserRole.MEMBER)
    ).scalar() or 0

    total_users: int = db.execute(select(func.count(User.id))).scalar() or 0

    borrowed_books: int = db.execute(
        select(func.count(BorrowingRecord.id)).where(
            BorrowingRecord.status == BorrowingStatus.BORROWED,
            BorrowingRecord.return_date.is_(None),
        )
    ).scalar() or 0

    overdue_books: int = db.execute(
        select(func.count(BorrowingRecord.id)).where(
            BorrowingRecord.return_date.is_(None),
            BorrowingRecord.due_date < now,
        )
    ).scalar() or 0

    total_returned: int = db.execute(
        select(func.count(BorrowingRecord.id)).where(
            BorrowingRecord.status == BorrowingStatus.RETURNED
        )
    ).scalar() or 0

    total_fines_val = db.execute(
        select(func.coalesce(func.sum(BorrowingRecord.fine_amount), Decimal("0.00")))
    ).scalar()
    total_fines: Decimal = Decimal(str(total_fines_val or "0.00"))

    return DashboardStatisticsSchema(
        total_books=total_books,
        available_books=available_books,
        borrowed_books=borrowed_books,
        overdue_books=overdue_books,
        total_members=total_members,
        total_copies=total_copies,
        available_copies=available_copies,
        total_users=total_users,
        total_borrowed=borrowed_books,
        total_overdue=overdue_books,
        total_returned=total_returned,
        total_fines=total_fines,
    )


def list_users(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
) -> UserListResponse:
    """Retrieve a paginated list of users for administration.

    Args:
        db: Active database session.
        page: Page number (1-indexed).
        page_size: Items per page.
        search: Optional search term matching email, first_name, or last_name.
        role: Optional filter by UserRole.

    Returns:
        UserListResponse: Paginated user list with safe attributes.

    Raises:
        BadRequestError: If page or page_size values are invalid.
    """
    if page < 1:
        raise BadRequestError("Page number must be greater than or equal to 1", code="invalid_page")
    if page_size < 1 or page_size > 100:
        raise BadRequestError("Page size must be between 1 and 100", code="invalid_page_size")

    count_stmt = select(func.count(User.id))

    if search:
        s = f"%{search.strip().lower()}%"
        count_stmt = count_stmt.where(
            func.lower(User.email).like(s)
            | func.lower(User.first_name).like(s)
            | func.lower(User.last_name).like(s)
        )

    if role is not None:
        count_stmt = count_stmt.where(User.role == role)

    total: int = db.execute(count_stmt).scalar() or 0

    if total == 0:
        return UserListResponse(items=[], page=page, page_size=page_size, total=0)

    query = select(User)

    if search:
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(User.email).like(s)
            | func.lower(User.first_name).like(s)
            | func.lower(User.last_name).like(s)
        )

    if role is not None:
        query = query.where(User.role == role)

    query = query.order_by(User.created_at.desc(), User.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    users = db.execute(query).scalars().all()
    items = [UserOut.model_validate(u) for u in users]

    return UserListResponse(items=items, page=page, page_size=page_size, total=total)


def get_user_details(db: Session, user_id: int) -> UserOut:
    """Retrieve details for a single user by primary key.

    Args:
        db: Active database session.
        user_id: Primary key of the target user.

    Returns:
        UserOut: Safe public user payload.

    Raises:
        NotFoundError: If the user does not exist.
    """
    user: User | None = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", code="user_not_found")
    return UserOut.model_validate(user)


def change_user_role(
    db: Session, current_admin: User, user_id: int, payload: UserRoleUpdate
) -> UserOut:
    """Change the role of a user.

    Args:
        db: Active database session.
        current_admin: Authenticated admin issuing the update.
        user_id: Target user's primary key.
        payload: Validated role payload.

    Returns:
        UserOut: Updated user representation.

    Raises:
        ConflictError: If an admin attempts to remove their own administrative role.
        NotFoundError: If the target user does not exist.
    """
    if user_id == current_admin.id and payload.role != UserRole.ADMIN:
        raise ConflictError(
            "Admins are not allowed to remove their own administrative role",
            code="self_demotion_forbidden",
        )

    user: User | None = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", code="user_not_found")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


def delete_user(db: Session, current_admin: User, user_id: int) -> Dict[str, Any]:
    """Safely delete a user account if no historical borrowing records exist.

    Args:
        db: Active database session.
        current_admin: Authenticated admin issuing the request.
        user_id: Target user's primary key.

    Returns:
        dict: Confirmation message.

    Raises:
        ConflictError: If the admin attempts self-deletion or if the user has borrowing history.
        NotFoundError: If the target user does not exist.
    """
    if user_id == current_admin.id:
        raise ConflictError("Admins cannot delete their own account", code="self_deletion_forbidden")

    user: User | None = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found", code="user_not_found")

    has_borrowing_history: bool = (
        db.execute(
            select(func.count(BorrowingRecord.id)).where(BorrowingRecord.user_id == user_id)
        ).scalar()
        or 0
    ) > 0

    if has_borrowing_history:
        raise ConflictError(
            "Cannot delete user: user account has associated historical borrowing records",
            code="user_has_borrowing_history",
        )

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully", "user_id": user_id}


# ============================================================================
# BOOK CATALOG & INVENTORY MANAGEMENT CONTROLLERS
# ============================================================================


def list_books(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    genre: Optional[str] = None,
    available: Optional[bool] = None,
) -> BookListResponse:
    """Retrieve a paginated list of books for catalog and inventory management.

    Args:
        db: Active database session.
        page: Page number (1-indexed).
        page_size: Items per page.
        search: Optional search term matching title, author, isbn, or genre.
        genre: Optional exact/case-insensitive genre filter.
        available: Optional filter for available_quantity > 0 or == 0.

    Returns:
        BookListResponse: Paginated list of books.

    Raises:
        BadRequestError: If page or page_size values are invalid.
    """
    if page < 1:
        raise BadRequestError("Page number must be greater than or equal to 1", code="invalid_page")
    if page_size < 1 or page_size > 100:
        raise BadRequestError("Page size must be between 1 and 100", code="invalid_page_size")

    count_stmt = select(func.count(Book.id))

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        count_stmt = count_stmt.where(
            func.lower(Book.title).like(s)
            | func.lower(Book.author).like(s)
            | func.lower(Book.isbn).like(s)
            | func.lower(Book.genre).like(s)
        )

    if genre and genre.strip():
        g = genre.strip().lower()
        count_stmt = count_stmt.where(func.lower(Book.genre) == g)

    if available is True:
        count_stmt = count_stmt.where(Book.available_quantity > 0)
    elif available is False:
        count_stmt = count_stmt.where(Book.available_quantity == 0)

    total: int = db.execute(count_stmt).scalar() or 0

    if total == 0:
        return BookListResponse(items=[], page=page, page_size=page_size, total=0)

    query = select(Book)

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(Book.title).like(s)
            | func.lower(Book.author).like(s)
            | func.lower(Book.isbn).like(s)
            | func.lower(Book.genre).like(s)
        )

    if genre and genre.strip():
        g = genre.strip().lower()
        query = query.where(func.lower(Book.genre) == g)

    if available is True:
        query = query.where(Book.available_quantity > 0)
    elif available is False:
        query = query.where(Book.available_quantity == 0)

    query = query.order_by(Book.title.asc(), Book.id.asc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    books = db.execute(query).scalars().all()
    items = [BookOut.model_validate(b) for b in books]

    return BookListResponse(items=items, page=page, page_size=page_size, total=total)


def get_book_details(db: Session, book_id: int) -> BookOut:
    """Retrieve details for a single book by primary key.

    Args:
        db: Active database session.
        book_id: Primary key of the target book.

    Returns:
        BookOut: Complete public representation of the book.

    Raises:
        NotFoundError: If the book does not exist.
    """
    book: Book | None = db.get(Book, book_id)
    if book is None:
        raise NotFoundError("Book not found", code="book_not_found")
    return BookOut.model_validate(book)


def create_book(db: Session, payload: BookCreate) -> BookOut:
    """Add a new book to the library catalog with validated inventory.

    Args:
        db: Active database session.
        payload: Validated book creation payload.

    Returns:
        BookOut: Representation of the created book.

    Raises:
        BadRequestError: If total_quantity or available_quantity are invalid.
        ConflictError: If a book with the given ISBN already exists.
    """
    if payload.total_quantity < 1:
        raise BadRequestError("total_quantity must be at least 1", code="invalid_quantity")

    if payload.available_quantity is None:
        available_qty = payload.total_quantity
    else:
        available_qty = payload.available_quantity
        if available_qty < 0 or available_qty > payload.total_quantity:
            raise BadRequestError(
                "available_quantity must be between 0 and total_quantity", code="invalid_quantity"
            )

    isbn_clean = payload.isbn.strip()
    existing = db.execute(
        select(Book).where(func.lower(Book.isbn) == isbn_clean.lower())
    ).scalar_one_or_none()

    if existing is not None:
        raise ConflictError("A book with this ISBN already exists", code="duplicate_isbn")

    book = Book(
        title=payload.title.strip(),
        author=payload.author.strip(),
        isbn=isbn_clean,
        genre=payload.genre.strip() if payload.genre and payload.genre.strip() else None,
        description=payload.description,
        total_quantity=payload.total_quantity,
        available_quantity=available_qty,
        published_year=payload.published_year,
    )

    db.add(book)
    db.commit()
    db.refresh(book)
    return BookOut.model_validate(book)


def update_book(db: Session, book_id: int, payload: BookUpdate) -> BookOut:
    """Update catalog metadata and inventory quantities for a book.

    Args:
        db: Active database session.
        book_id: Primary key of the target book.
        payload: Validated update payload.

    Returns:
        BookOut: Updated book representation.

    Raises:
        NotFoundError: If the book does not exist.
        ConflictError: If ISBN is duplicate or total_quantity is reduced below borrowed count.
        BadRequestError: If quantities are invalid.
    """
    statement = select(Book).where(Book.id == book_id).with_for_update()
    book: Book | None = db.execute(statement).scalar_one_or_none()
    if book is None:
        raise NotFoundError("Book not found", code="book_not_found")

    if payload.isbn is not None:
        new_isbn = payload.isbn.strip()
        if new_isbn.lower() != book.isbn.lower():
            dup = db.execute(
                select(Book).where(func.lower(Book.isbn) == new_isbn.lower(), Book.id != book_id)
            ).scalar_one_or_none()
            if dup is not None:
                raise ConflictError("A book with this ISBN already exists", code="duplicate_isbn")

    if payload.title is not None:
        book.title = payload.title.strip()
    if payload.author is not None:
        book.author = payload.author.strip()
    if payload.isbn is not None:
        book.isbn = payload.isbn.strip()
    if payload.genre is not None:
        book.genre = payload.genre.strip() if payload.genre.strip() else None
    if payload.description is not None:
        book.description = payload.description
    if payload.published_year is not None:
        book.published_year = payload.published_year

    borrowed_copies = book.total_quantity - book.available_quantity

    new_total = payload.total_quantity if payload.total_quantity is not None else book.total_quantity

    if new_total < 0:
        raise BadRequestError("total_quantity cannot be negative", code="invalid_quantity")

    if new_total < borrowed_copies:
        raise ConflictError(
            f"Cannot reduce total quantity to {new_total}: {borrowed_copies} copies are currently borrowed",
            code="quantity_below_borrowed",
        )

    if payload.available_quantity is not None:
        new_avail = payload.available_quantity
        if new_avail < 0:
            raise BadRequestError("available_quantity cannot be negative", code="invalid_quantity")
        if new_avail > new_total:
            raise BadRequestError(
                "available_quantity cannot exceed total_quantity", code="invalid_quantity"
            )
        if new_total - new_avail < borrowed_copies:
            raise ConflictError(
                "available_quantity conflicts with currently active borrowings",
                code="invalid_inventory_quantity",
            )
        book.total_quantity = new_total
        book.available_quantity = new_avail
    else:
        book.total_quantity = new_total
        book.available_quantity = new_total - borrowed_copies

    db.commit()
    db.refresh(book)
    return BookOut.model_validate(book)


def delete_book(db: Session, book_id: int) -> Dict[str, Any]:
    """Safely delete a book if no active or historical borrowing records exist.

    Args:
        db: Active database session.
        book_id: Primary key of the target book.

    Returns:
        dict: Deletion confirmation message.

    Raises:
        NotFoundError: If the book does not exist.
        ConflictError: If active or historical borrowing records exist.
    """
    book: Book | None = db.get(Book, book_id)
    if book is None:
        raise NotFoundError("Book not found", code="book_not_found")

    active_count: int = (
        db.execute(
            select(func.count(BorrowingRecord.id)).where(
                BorrowingRecord.book_id == book_id,
                BorrowingRecord.status == BorrowingStatus.BORROWED,
            )
        ).scalar()
        or 0
    )

    if active_count > 0:
        raise ConflictError(
            "Cannot delete book: active borrowing records exist for this book",
            code="book_has_active_borrowings",
        )

    total_count: int = (
        db.execute(
            select(func.count(BorrowingRecord.id)).where(BorrowingRecord.book_id == book_id)
        ).scalar()
        or 0
    )

    if total_count > 0:
        raise ConflictError(
            "Cannot delete book: historical borrowing records exist for this book",
            code="book_has_borrowing_history",
        )

    db.delete(book)
    db.commit()
    return {"message": "Book deleted successfully", "book_id": book_id}


# ============================================================================
# ADMIN BORROWING HISTORY CONTROLLERS
# ============================================================================


def list_admin_borrowings(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status: Optional[BorrowingStatus] = None,
    user_id: Optional[int] = None,
    from_date: Optional[str | datetime | date] = None,
    to_date: Optional[str | datetime | date] = None,
) -> AdminBorrowingHistoryResponse:
    """Retrieve a paginated list of borrowing records across all users for administrative reporting.

    Args:
        db: Active database session.
        page: Page number (1-indexed).
        page_size: Items per page.
        search: Optional search term matching member name/email or book title/author/ISBN.
        status: Optional status filter (BORROWED, RETURNED, OVERDUE).
        user_id: Optional member ID filter.
        from_date: Optional start date filter on issue_date.
        to_date: Optional end date filter on issue_date.

    Returns:
        AdminBorrowingHistoryResponse: Paginated borrowing records with book and member information.

    Raises:
        BadRequestError: If page, page_size, or date parameters are invalid.
    """
    if page < 1:
        raise BadRequestError("Page number must be greater than or equal to 1", code="invalid_page")
    if page_size < 1 or page_size > 100:
        raise BadRequestError("Page size must be between 1 and 100", code="invalid_page_size")

    parsed_from = _parse_date_param(from_date, "from_date", is_end_of_day=False)
    parsed_to = _parse_date_param(to_date, "to_date", is_end_of_day=True)

    if parsed_from is not None and parsed_to is not None:
        if parsed_from > parsed_to:
            raise BadRequestError("from_date must be less than or equal to to_date", code="invalid_date_range")

    count_stmt = (
        select(func.count(BorrowingRecord.id))
        .join(BorrowingRecord.user)
        .join(BorrowingRecord.book)
    )

    if status is not None:
        count_stmt = count_stmt.where(BorrowingRecord.status == status)

    if user_id is not None:
        count_stmt = count_stmt.where(BorrowingRecord.user_id == user_id)

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        count_stmt = count_stmt.where(
            func.lower(User.email).like(s)
            | func.lower(User.first_name).like(s)
            | func.lower(User.last_name).like(s)
            | func.lower(Book.title).like(s)
            | func.lower(Book.author).like(s)
            | func.lower(Book.isbn).like(s)
        )

    if parsed_from is not None:
        count_stmt = count_stmt.where(BorrowingRecord.issue_date >= parsed_from)

    if parsed_to is not None:
        count_stmt = count_stmt.where(BorrowingRecord.issue_date <= parsed_to)

    total: int = db.execute(count_stmt).scalar() or 0

    if total == 0:
        return AdminBorrowingHistoryResponse(items=[], page=page, page_size=page_size, total=0)

    query = (
        select(BorrowingRecord)
        .join(BorrowingRecord.user)
        .join(BorrowingRecord.book)
        .options(
            joinedload(BorrowingRecord.user),
            joinedload(BorrowingRecord.book),
        )
    )

    if status is not None:
        query = query.where(BorrowingRecord.status == status)

    if user_id is not None:
        query = query.where(BorrowingRecord.user_id == user_id)

    if search and search.strip():
        s = f"%{search.strip().lower()}%"
        query = query.where(
            func.lower(User.email).like(s)
            | func.lower(User.first_name).like(s)
            | func.lower(User.last_name).like(s)
            | func.lower(Book.title).like(s)
            | func.lower(Book.author).like(s)
            | func.lower(Book.isbn).like(s)
        )

    if parsed_from is not None:
        query = query.where(BorrowingRecord.issue_date >= parsed_from)

    if parsed_to is not None:
        query = query.where(BorrowingRecord.issue_date <= parsed_to)

    query = query.order_by(BorrowingRecord.issue_date.desc(), BorrowingRecord.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    records = db.execute(query).scalars().all()
    items = [AdminBorrowingHistoryItem.model_validate(rec) for rec in records]

    return AdminBorrowingHistoryResponse(items=items, page=page, page_size=page_size, total=total)
