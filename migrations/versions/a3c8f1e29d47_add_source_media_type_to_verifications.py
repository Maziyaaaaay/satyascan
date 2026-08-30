"""add source_media_type to verifications

Revision ID: a3c8f1e29d47
Revises: f7a9c3e1b2d4
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
import app.db.base


# revision identifiers, used by Alembic.
revision: str = 'a3c8f1e29d47'
down_revision: Union[str, Sequence[str], None] = 'f7a9c3e1b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Idempotency check, not just style: confirmed live in production that
    # SQLite's non-transactional DDL (see every `alembic upgrade` run's own
    # "Will assume non-transactional DDL" log line) means a container killed
    # between this ALTER TABLE succeeding and Alembic recording the new
    # version leaves alembic_version still on the old revision - the next
    # deploy then retries this exact migration against a DB that already has
    # the column, and ADD COLUMN isn't idempotent on its own, so it crash-
    # loops forever ("duplicate column name: source_media_type") until fixed.
    # Checking first makes a retry always safe regardless of how much of a
    # prior attempt actually landed.
    conn = op.get_bind()
    existing_columns = {col["name"] for col in inspect(conn).get_columns("verifications")}
    if "source_media_type" not in existing_columns:
        op.add_column(
            'verifications',
            sa.Column('source_media_type', sa.String(length=16), nullable=False, server_default='text'),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('verifications', 'source_media_type')
