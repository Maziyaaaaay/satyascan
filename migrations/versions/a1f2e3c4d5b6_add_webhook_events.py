"""add webhook_events

Revision ID: a1f2e3c4d5b6
Revises: e355b647054d
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.base


# revision identifiers, used by Alembic.
revision: str = 'a1f2e3c4d5b6'
down_revision: Union[str, Sequence[str], None] = 'e355b647054d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('webhook_events',
    sa.Column('external_message_id', sa.String(), nullable=False),
    sa.Column('id', app.db.base.GUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_events_external_message_id'), 'webhook_events', ['external_message_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_webhook_events_external_message_id'), table_name='webhook_events')
    op.drop_table('webhook_events')
