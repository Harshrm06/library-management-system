"""Add the borrowing_records table

Revision ID: 002
Revises: 001
Create Date: 2026-10-03

Creates ``borrowing_records``, the audit trail for a copy that leaves and returns
to the library:

* ``borrowing_records`` - one loan per row, with foreign keys to ``users`` and
  ``books``, a 14 day loan window, a nullable return date, a status enum and a
  non-negative fine, plus indexes on ``user_id``, ``book_id`` and ``status``.

The fine is ``Numeric(10, 2)`` so money never picks up binary floating point
error, and the status is a native enum stored with its uppercase values.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the borrowing_records table with its indexes and constraints."""
    op.create_table(
        "borrowing_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("issue_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("return_date", sa.DateTime(), nullable=True),
        sa.Column(
            "status",
            # `create_constraint=True` mirrors the model: on SQLite, which has no
            # native enum, this is what emits
            # `CHECK (status IN ('BORROWED', 'RETURNED', 'OVERDUE'))` so the
            # database rejects a status outside the enum. MySQL and PostgreSQL
            # get a real enum type regardless.
            sa.Enum(
                "BORROWED",
                "RETURNED",
                "OVERDUE",
                name="borrowing_status",
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("fine_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_borrowing_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["book_id"], ["books.id"], name="fk_borrowing_book_id"
        ),
        # The same two rules the model declares, so a row written by raw SQL is
        # held to them too.
        sa.CheckConstraint(
            "due_date >= issue_date", name="ck_borrowing_due_after_issue"
        ),
        sa.CheckConstraint(
            "fine_amount >= 0", name="ck_borrowing_fine_non_negative"
        ),
    )
    op.create_index(
        "ix_borrowing_user_id", "borrowing_records", ["user_id"], unique=False
    )
    op.create_index(
        "ix_borrowing_book_id", "borrowing_records", ["book_id"], unique=False
    )
    op.create_index(
        "ix_borrowing_status", "borrowing_records", ["status"], unique=False
    )


def downgrade() -> None:
    """Drop the borrowing_records table and its indexes."""
    op.drop_index("ix_borrowing_status", table_name="borrowing_records")
    op.drop_index("ix_borrowing_book_id", table_name="borrowing_records")
    op.drop_index("ix_borrowing_user_id", table_name="borrowing_records")
    op.drop_table("borrowing_records")