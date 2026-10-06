"""Alembic migration environment.

Migrations are generated from the SQLAlchemy metadata declared in
``app/models``. The database URL always comes from ``app.config`` (i.e. from
``backend/.env``) so credentials stay out of ``alembic.ini``.

Commands (run from ``backend/``)::

    alembic revision --autogenerate -m "Add fine_amount to borrowing_records"
    alembic upgrade head
    alembic downgrade -1
"""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path
from typing import Any, Optional

from alembic import context
from sqlalchemy import engine_from_config, pool

BACKEND_ROOT: Path = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (imports User, Book and friends)
from app.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic interpolates '%' in the DSN, so it must be escaped for configparser.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

target_metadata = Base.metadata

COMPARISON_OPTIONS: dict[str, Any] = {
    "compare_type": True,
    "compare_server_default": True,
    "compare_indexes": True,
}


def include_object(object_: Any, name: Optional[str], type_: str, reflected: bool, compare_to: Any) -> bool:
    """Decide whether an object belongs in a migration.

    Args:
        object_: The schema object Alembic is considering.
        name: Name of the object.
        type_: ``"table"``, ``"column"``, ``"index"`` and so on.
        reflected: ``True`` when the object exists only in the database.
        compare_to: The metadata counterpart, when there is one.

    Returns:
        bool: ``True`` to include the object in the migration.
    """
    if type_ == "table" and name in {"alembic_version"}:
        return False
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to a database."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        **COMPARISON_OPTIONS,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            **COMPARISON_OPTIONS,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
