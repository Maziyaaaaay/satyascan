"""add c2pa fields to images

Revision ID: f7a9c3e1b2d4
Revises: a1f2e3c4d5b6
Create Date: 2026-08-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.base


# revision identifiers, used by Alembic.
revision: str = 'f7a9c3e1b2d4'
down_revision: Union[str, Sequence[str], None] = 'a1f2e3c4d5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'images', sa.Column('c2pa_has_manifest', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column('images', sa.Column('c2pa_generator', sa.String(length=200), nullable=True))
    op.add_column('images', sa.Column('c2pa_digital_source_type', sa.String(length=300), nullable=True))
    op.add_column(
        'images', sa.Column('c2pa_is_ai_indicated', sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column('images', sa.Column('c2pa_summary', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('images', 'c2pa_summary')
    op.drop_column('images', 'c2pa_is_ai_indicated')
    op.drop_column('images', 'c2pa_digital_source_type')
    op.drop_column('images', 'c2pa_generator')
    op.drop_column('images', 'c2pa_has_manifest')
