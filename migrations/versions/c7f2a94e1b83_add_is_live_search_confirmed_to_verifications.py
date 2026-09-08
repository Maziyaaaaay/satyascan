"""add is_live_search_confirmed to verifications

Revision ID: c7f2a94e1b83
Revises: a3c8f1e29d47
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import app.db.base


# revision identifiers, used by Alembic.
revision: str = 'c7f2a94e1b83'
down_revision: Union[str, Sequence[str], None] = 'a3c8f1e29d47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Idempotency check: see a3c8f1e29d47's migration for why this matters
    # on SQLite's non-transactional DDL - confirmed live as the cause of a
    # real crash-loop when a retry hit an ADD COLUMN that had already landed.
    conn = op.get_bind()
    existing_columns = {col["name"] for col in inspect(conn).get_columns("verifications")}
    if "is_live_search_confirmed" not in existing_columns:
        op.add_column(
            'verifications',
            sa.Column('is_live_search_confirmed', sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('verifications', 'is_live_search_confirmed')
