"""SQLAlchemy engine, session factory and declarative base."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Declarative base class shared by every ORM model."""


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime.

    Models use this for ``created_at`` / ``updated_at`` defaults. The result is
    naive on purpose: MySQL ``DATETIME`` columns do not store a time zone, so
    keeping every timestamp naive avoids aware/naive comparison errors.

    Returns:
        datetime: The current UTC time without a tzinfo.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def build_engine_kwargs() -> Dict[str, Any]:
    """Return engine options for the configured database URL.

    Pool sizing is only applied to dialects that support a sized queue pool;
    SQLite (used by the test suite) uses its own connection strategies.

    Returns:
        dict: Keyword arguments for :func:`sqlalchemy.create_engine`.
    """
    kwargs: Dict[str, Any] = {
        "echo": settings.db_echo,
        "pool_pre_ping": True,
        "future": True,
    }
    backend: str = make_url(settings.database_url).get_backend_name()
    if backend != "sqlite":
        kwargs.update(
            pool_recycle=settings.db_pool_recycle,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )
    return kwargs


engine = create_engine(settings.database_url, **build_engine_kwargs())

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session.

    Yields:
        Session: A session bound to the request lifecycle.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()