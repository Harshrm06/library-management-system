"""Fix schema drift on books

Revision ID: 003
Revises: 002
Create Date: 2026-10-03

Closes the two differences ``alembic check`` reported between the ORM models and
the schema built by migrations 001 and 002.

1. ``books.genre`` index

   ``app/models/book.py`` declares ``Index("ix_books_genre", "genre")`` so the
   catalog's exact-match genre filter is served by an index, but migration 001
   only created the ``isbn``, ``title`` and ``author`` indexes. The model and the
   database therefore disagreed, and a database built purely from migrations had
   no genre index at all. This revision creates it.

2. ``books.description`` column type

   No change is needed here, and the direction is the opposite of what the drift
   report first appears to suggest. Migration 001 already creates the column as
   ``sa.Text()`` (``001_initial_migration.py:35``), so a migrated database holds
   ``TEXT``; it was the *model* that was narrower, declaring
   ``String(1000)``. Alembic reports a ``modify_type`` because it compares the
   model's type against the database's, so the mismatch was fixed in
   ``app/models/book.py`` by declaring the column as ``Text()`` - which is also
   what makes the column able to hold a full LONGTEXT on MySQL.

   Widening the column here instead would have been a no-op on SQLite and MySQL,
   both of which already store ``TEXT``, and would have left the drift in place.

Note that the API still validates ``description`` at 1000 characters in
``app/schemas/book_schema.py``, so the column can store more than a client may
currently send. Relaxing that limit is a separate, deliberate product decision
and is deliberately not bundled into a schema-drift fix.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: Index the model declares on ``books.genre`` but no migration created.
GENRE_INDEX: str = "ix_books_genre"

#: Table the index belongs to.
BOOKS_TABLE: str = "books"


def upgrade() -> None:
    """Add the missing genre index.

    ``op.create_index`` maps to a plain ``CREATE INDEX`` on SQLite and MySQL, so
    no batch mode is needed: unlike a column type change, adding an index needs
    no table rebuild. The index is written through ``IF NOT EXISTS`` semantics by
    checking the current state first, so re-running against a database that
    already has it is harmless.
    """
    inspector = sa.inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(BOOKS_TABLE)}
    if GENRE_INDEX not in existing:
        op.create_index(GENRE_INDEX, BOOKS_TABLE, ["genre"], unique=False)


def downgrade() -> None:
    """Drop the genre index.

    ``books.description`` is deliberately left alone: it is ``TEXT`` in the model
    and was ``TEXT`` before this revision, so there is nothing to reverse. Only
    the index is removed.
    """
    inspector = sa.inspect(op.get_bind())
    existing = {index["name"] for index in inspector.get_indexes(BOOKS_TABLE)}
    if GENRE_INDEX in existing:
        op.drop_index(GENRE_INDEX, table_name=BOOKS_TABLE)
