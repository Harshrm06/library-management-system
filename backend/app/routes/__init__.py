"""API route package."""

from app.routes.admin_routes import router as admin_router
from app.routes.auth_routes import router as auth_router
from app.routes.borrow_routes import router as borrow_router
from app.routes.return_routes import router as return_router

__all__ = ["admin_router", "auth_router", "borrow_router", "return_router"]