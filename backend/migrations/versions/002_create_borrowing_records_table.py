"""create_borrowing_records_table

Revision ID: 002_borrowing_records
Revises: 001_users_books
Create Date: 2026-10-06 12:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_borrowing_records'
down_revision: Union[str, None] = '001_users_books'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'borrowing_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.Integer(), nullable=False),
        sa.Column('issue_date', sa.DateTime(), nullable=False),
        sa.Column('due_date', sa.DateTime(), nullable=False),
        sa.Column('return_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('BORROWED', 'RETURNED', 'OVERDUE', name='borrowing_status'), nullable=False),
        sa.Column('fine_amount', sa.Numeric(precision=10, scale=2), server_default='0.00', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['book_id'], ['books.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_borrowing_records_book_id'), 'borrowing_records', ['book_id'], unique=False)
    op.create_index(op.f('ix_borrowing_records_status'), 'borrowing_records', ['status'], unique=False)
    op.create_index(op.f('ix_borrowing_records_user_id'), 'borrowing_records', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_borrowing_records_user_id'), table_name='borrowing_records')
    op.drop_index(op.f('ix_borrowing_records_status'), table_name='borrowing_records')
    op.drop_index(op.f('ix_borrowing_records_book_id'), table_name='borrowing_records')
    op.drop_table('borrowing_records')
