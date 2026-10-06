"""Create the database schema and load the starter catalogue and accounts.

The schema is built by Alembic (``alembic upgrade head``) rather than
``Base.metadata.create_all``. The two are not interchangeable here: the project
owns named CHECK constraints and an explicit migration history, and creating the
tables directly would leave ``alembic_version`` empty, so the next
``alembic upgrade head`` would try to create tables that already exist and fail.

The seed is idempotent. Books are matched on ISBN and users on email, so running
this repeatedly tops the catalogue up to the intended counts instead of
duplicating rows, and it is safe to re-run after adding a title.

Run with::

    python seed_data.py            create the schema and seed if needed
    python seed_data.py --reset    drop every table first, then recreate
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models.book import Book  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.utils.bcrypt_utils import hash_password  # noqa: E402

#: Starter catalogue: ``(title, author, isbn, genre, year, copies, description)``.
SAMPLE_BOOKS: tuple[tuple[str, str, str, str, int, int, str], ...] = (
    (
        "The Great Gatsby",
        "F. Scott Fitzgerald",
        "9780743273565",
        "Classic",
        1925,
        5,
        "A Jazz Age millionaire and the light he chases across the bay.",
    ),
    (
        "To Kill a Mockingbird",
        "Harper Lee",
        "9780061120084",
        "Classic",
        1960,
        3,
        "A lawyer defends a Black man in the Depression-era South.",
    ),
    (
        "1984",
        "George Orwell",
        "9780451524935",
        "Dystopian",
        1949,
        4,
        "A society that abolishes privacy in the name of progress.",
    ),
    (
        "Pride and Prejudice",
        "Jane Austen",
        "9780141439518",
        "Classic",
        1813,
        6,
        "First impressions, and a revision of them, in Regency England.",
    ),
    (
        "The Catcher in the Rye",
        "J. D. Salinger",
        "9780316769488",
        "Classic",
        1951,
        2,
        "A teenage narrator decides everyone else is a phoney.",
    ),
    (
        "Jane Eyre",
        "Charlotte Bronte",
        "9780142437209",
        "Classic",
        1847,
        4,
        "An orphaned governess claims a life of her own.",
    ),
    (
        "Wuthering Heights",
        "Emily Bronte",
        "9780142437223",
        "Classic",
        1847,
        3,
        "A moorside house, and two families bound to it by more than blood.",
    ),
    (
        "The Hobbit",
        "J. R. R. Tolkien",
        "9780547928227",
        "Fantasy",
        1937,
        5,
        "A hobbit, a map, and a dragon that has to be dealt with.",
    ),
)

#: Starter accounts: ``(email, password, first, last, role)``.
ADMIN_EMAIL = "admin@library.local"
ADMIN_PASSWORD = "Admin123"
MEMBER_EMAIL = "member@library.local"
MEMBER_PASSWORD = "Member123"


def upgrade_schema() -> None:
    """Bring the database up to the latest migration.

    Raises:
        SystemExit: If the migration fails, usually because the database file
            cannot be created or the MySQL server is unreachable.
    """
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    # Point Alembic at whatever DATABASE_URL the app resolved, so the migration
    # and the application can never disagree about which database is in use.
    config.set_main_option("sqlalchemy.url", settings.database_url)
    try:
        command.upgrade(config, "head")
    except Exception as error:  # noqa: BLE001 - reported as a clean CLI failure
        raise SystemExit(
            f"[ERROR] Could not apply migrations: {error}\n"
            f"        DATABASE_URL={settings.database_url}"
        ) from error


def drop_everything() -> None:
    """Drop all tables, used only by ``--reset``."""
    Base.metadata.drop_all(bind=engine)


def seed_books() -> int:
    """Insert any missing titles.

    Returns:
        int: How many books were actually created.
    """
    created = 0
    session = SessionLocal()
    try:
        for title, author, isbn, genre, year, copies, description in SAMPLE_BOOKS:
            exists = session.execute(
                select(func.count()).select_from(Book).where(Book.isbn == isbn)
            ).scalar_one()
            if exists:
                continue
            session.add(
                Book(
                    title=title,
                    author=author,
                    isbn=isbn,
                    genre=genre,
                    description=description,
                    published_year=year,
                    total_quantity=copies,
                    available_quantity=copies,
                )
            )
            created += 1
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise SystemExit(f"[ERROR] Seeding books failed: {error}") from error
    finally:
        session.close()
    return created


def seed_users() -> int:
    """Create the administrator and member accounts if they are absent.

    Returns:
        int: How many users were actually created.
    """
    wanted = (
        (
            ADMIN_EMAIL,
            ADMIN_PASSWORD,
            "System",
            "Administrator",
            UserRole.ADMIN,
        ),
        (
            MEMBER_EMAIL,
            MEMBER_PASSWORD,
            "Sample",
            "Member",
            UserRole.MEMBER,
        ),
    )
    created = 0
    session = SessionLocal()
    try:
        for email, password, first, last, role in wanted:
            exists = session.execute(
                select(func.count()).select_from(User).where(User.email == email)
            ).scalar_one()
            if exists:
                continue
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(password),
                    first_name=first,
                    last_name=last,
                    role=role,
                    is_active=True,
                )
            )
            created += 1
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise SystemExit(f"[ERROR] Seeding users failed: {error}") from error
    finally:
        session.close()
    return created


def report() -> None:
    """Print the resulting counts and the login details."""
    session = SessionLocal()
    try:
        books = session.execute(select(func.count()).select_from(Book)).scalar_one()
        users = session.execute(select(func.count()).select_from(User)).scalar_one()
        admins = session.execute(
            select(func.count()).select_from(User).where(User.role == UserRole.ADMIN)
        ).scalar_one()
    finally:
        session.close()

    print()
    print("=" * 62)
    print("  Library Management System is ready")
    print("=" * 62)
    print(f"  Database : {settings.database_url}")
    print(f"  Books    : {books}")
    print(f"  Users    : {users} ({admins} admin)")
    print()
    print("  Sign in with either account:")
    print()
    print("    Administrator")
    print(f"      email    : {ADMIN_EMAIL}")
    print(f"      password : {ADMIN_PASSWORD}")
    print()
    print("    Member")
    print(f"      email    : {MEMBER_EMAIL}")
    print(f"      password : {MEMBER_PASSWORD}")
    print()
    print("  Start the API with:  uvicorn app.main:app --reload")
    print("  Interactive docs:    http://localhost:8000/docs")
    print()
    print("  These are development credentials. Change both passwords,")
    print("  and JWT_SECRET in .env, before exposing this to anyone.")
    print("=" * 62)


def main() -> int:
    """Parse arguments, build the schema and seed it.

    Returns:
        int: Process exit status.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop every table before creating the schema again",
    )
    args = parser.parse_args()

    print(f"[INFO] DATABASE_URL = {settings.database_url}")
    if args.reset:
        print("[INFO] --reset: dropping existing tables")
        drop_everything()

    print("[INFO] Applying migrations (alembic upgrade head)...")
    upgrade_schema()

    new_books = seed_books()
    new_users = seed_users()
    print(
        f"[INFO] Seeded {new_books} book(s) and {new_users} user(s) "
        f"({new_books + new_users} created, existing rows left alone)."
    )

    report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
