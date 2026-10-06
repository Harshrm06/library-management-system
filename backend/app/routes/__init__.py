"""API route package."""

from app.routes.auth_routes import router as auth_router
from app.routes.book_routes import router as book_router
from app.routes.borrowing_routes import router as borrowing_router

__all__ = ["auth_router", "book_router", "borrowing_router"]