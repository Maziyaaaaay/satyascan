"""add source_media_type to verifications

Revision ID: a3c8f1e29d47
Revises: f7a9c3e1b2d4
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.base


# revision identifiers, used by Alembic.
revision: str = 'a3c8f1e29d47'
down_revision: Union[str, Sequence[str], None] = 'f7a9c3e1b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'verifications',
        sa.Column('source_media_type', sa.String(length=16), nullable=False, server_default='text'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('verifications', 'source_media_type')
