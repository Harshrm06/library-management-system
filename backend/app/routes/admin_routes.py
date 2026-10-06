"""Admin API endpoints for dashboard stats, user management, book inventory management, and borrowing history."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.controllers import admin_controller
from app.database import get_db
from app.middleware.auth_middleware import require_role
from app.models.borrowing_record import BorrowingStatus
from app.models.user import User, UserRole
from app.schemas.book_schema import (
    BookCreate,
    BookListResponse,
    BookOut,
    BookUpdate,
)
from app.schemas.borrowing_schema import (
    AdminBorrowingHistoryResponse,
    DashboardStatisticsSchema,
)
from app.schemas.user_schema import UserListResponse, UserOut, UserRoleUpdate

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/dashboard/stats",
    response_model=DashboardStatisticsSchema,
    status_code=status.HTTP_200_OK,
    summary="Get admin dashboard statistics",
)
def get_dashboard_stats(
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> DashboardStatisticsSchema:
    """Return aggregate library metrics for administrative monitoring.

    Args:
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        DashboardStatisticsSchema: Aggregate library statistics.
    """
    return admin_controller.get_dashboard_statistics(db)


@router.get(
    "/users",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List library users with search and pagination",
)
def list_users(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Optional search term matching email/name"),
    role: Optional[str] = Query(default=None, description="Optional filter by UserRole"),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """Retrieve a paginated list of library users for administration.

    Args:
        page: Page number.
        page_size: Items per page.
        search: Optional search term.
        role: Optional role filter.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        UserListResponse: Paginated user listing without sensitive credentials.
    """
    parsed_role: Optional[UserRole] = None
    if role is not None and role.strip():
        r_clean = role.strip().lower()
        if r_clean in ("admin", "member"):
            parsed_role = UserRole(r_clean)
        else:
            raise RequestValidationError(
                [{"loc": ["query", "role"], "msg": f"Input should be 'admin' or 'member', got '{role}'"}]
            )

    return admin_controller.list_users(
        db, page=page, page_size=page_size, search=search, role=parsed_role
    )


@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Get user details by ID",
)
def get_user_details(
    user_id: int,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserOut:
    """Return user profile details.

    Args:
        user_id: Target user ID.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        UserOut: Public representation of the user.
    """
    return admin_controller.get_user_details(db, user_id)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserOut,
    status_code=status.HTTP_200_OK,
    summary="Change user role",
)
def change_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> UserOut:
    """Update a user's role (ADMIN or MEMBER).

    Args:
        user_id: Target user ID.
        payload: Validated role update payload.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        UserOut: Updated user profile.
    """
    return admin_controller.change_user_role(db, current_admin, user_id, payload)


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete user account",
)
def delete_user(
    user_id: int,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a user account if no historical borrowing records exist.

    Args:
        user_id: Target user ID.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        dict: Deletion confirmation message.
    """
    return admin_controller.delete_user(db, current_admin, user_id)


# ============================================================================
# BOOK CATALOG & INVENTORY MANAGEMENT ROUTE ENDPOINTS
# ============================================================================


@router.get(
    "/books",
    response_model=BookListResponse,
    status_code=status.HTTP_200_OK,
    summary="List library books with search, filtering and pagination",
)
def list_books(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Optional search term matching title/author/isbn/genre"),
    genre: Optional[str] = Query(default=None, description="Optional genre filter"),
    available: Optional[bool] = Query(default=None, description="Optional availability filter"),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> BookListResponse:
    """Retrieve a paginated list of books for administration.

    Args:
        page: Page number.
        page_size: Items per page.
        search: Optional search term.
        genre: Optional genre filter.
        available: Optional availability filter.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        BookListResponse: Paginated book listing with inventory details.
    """
    return admin_controller.list_books(
        db, page=page, page_size=page_size, search=search, genre=genre, available=available
    )


@router.get(
    "/books/{book_id}",
    response_model=BookOut,
    status_code=status.HTTP_200_OK,
    summary="Get book catalog details by ID",
)
def get_book_details(
    book_id: int,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> BookOut:
    """Return catalog and inventory info for a single book.

    Args:
        book_id: Target book ID.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        BookOut: Complete book information.
    """
    return admin_controller.get_book_details(db, book_id)


@router.post(
    "/books",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new book to catalog",
)
def create_book(
    payload: BookCreate,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> BookOut:
    """Create a new book entry in the library catalog.

    Args:
        payload: Book creation parameters.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        BookOut: Created book representation.
    """
    return admin_controller.create_book(db, payload)


@router.patch(
    "/books/{book_id}",
    response_model=BookOut,
    status_code=status.HTTP_200_OK,
    summary="Update book metadata or inventory levels",
)
@router.put(
    "/books/{book_id}",
    response_model=BookOut,
    status_code=status.HTTP_200_OK,
    summary="Update book metadata or inventory levels (PUT alias)",
)
def update_book(
    book_id: int,
    payload: BookUpdate,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> BookOut:
    """Update a book's catalog details and inventory quantities.

    Args:
        book_id: Target book ID.
        payload: Validated update payload.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        BookOut: Updated book representation.
    """
    return admin_controller.update_book(db, book_id, payload)


@router.delete(
    "/books/{book_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete book from catalog",
)
def delete_book(
    book_id: int,
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Delete a book from catalog if no active or historical borrowing records exist.

    Args:
        book_id: Target book ID.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        dict: Deletion confirmation message.
    """
    return admin_controller.delete_book(db, book_id)


# ============================================================================
# ADMIN BORROWING HISTORY ROUTE ENDPOINTS
# ============================================================================


@router.get(
    "/borrowings",
    response_model=AdminBorrowingHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="List borrowing history across all library members",
)
def list_admin_borrowings(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(default=None, description="Optional search query matching member or book"),
    status: Optional[str] = Query(default=None, description="Optional status filter (BORROWED, RETURNED, OVERDUE)"),
    user_id: Optional[int] = Query(default=None, description="Optional member ID filter"),
    from_date: Optional[str] = Query(default=None, description="Optional start issue_date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(default=None, description="Optional end issue_date (YYYY-MM-DD)"),
    current_admin: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> AdminBorrowingHistoryResponse:
    """Retrieve a paginated history of all member borrowing records for administrative reporting.

    Args:
        page: Page number.
        page_size: Items per page.
        search: Optional search term.
        status: Optional status filter.
        user_id: Optional member filter.
        from_date: Optional start issue_date.
        to_date: Optional end issue_date.
        current_admin: Authenticated user with ADMIN role.
        db: Database session.

    Returns:
        AdminBorrowingHistoryResponse: Paginated borrowing records with member and book details.
    """
    parsed_status: Optional[BorrowingStatus] = None
    if status is not None and status.strip():
        s_clean = status.strip().upper()
        if s_clean in ("BORROWED", "RETURNED", "OVERDUE"):
            parsed_status = BorrowingStatus(s_clean)
        else:
            raise RequestValidationError(
                [{"loc": ["query", "status"], "msg": f"Input should be 'BORROWED', 'RETURNED' or 'OVERDUE', got '{status}'"}]
            )

    return admin_controller.list_admin_borrowings(
        db,
        page=page,
        page_size=page_size,
        search=search,
        status=parsed_status,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
    )
