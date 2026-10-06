"""ORM model package.

Every model is imported and re-exported here so migrations, controllers and
schemas can rely on a single import point, and so Alembic's ``import app.models``
sees every table before it compares against the database::

    from app.models import Book, BorrowingRecord, BorrowingStatus, User, UserRole
"""

from app.models.book import Book
from app.models.borrowing_record import BorrowingRecord, BorrowingStatus
from app.models.user import User, UserRole

__all__ = ["Book", "BorrowingRecord", "BorrowingStatus", "User", "UserRole"]