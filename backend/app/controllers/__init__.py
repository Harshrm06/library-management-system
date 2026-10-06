"""Controller package holding business logic."""

from app.controllers.admin_controller import (
    change_user_role,
    create_book,
    delete_book,
    delete_user,
    get_book_details,
    get_dashboard_statistics,
    get_user_details,
    list_admin_borrowings,
    list_books,
    list_users,
    update_book,
)
from app.controllers.auth_controller import (
    authenticate_user,
    get_user_by_email,
    get_user_by_id,
    register_user,
)
from app.controllers.borrow_controller import (
    borrow_book,
    get_user_borrowing_history,
    return_book,
)

__all__ = [
    "authenticate_user",
    "borrow_book",
    "change_user_role",
    "create_book",
    "delete_book",
    "delete_user",
    "get_book_details",
    "get_dashboard_statistics",
    "get_user_by_email",
    "get_user_by_id",
    "get_user_details",
    "get_user_borrowing_history",
    "list_admin_borrowings",
    "list_books",
    "list_users",
    "register_user",
    "return_book",
    "update_book",
]