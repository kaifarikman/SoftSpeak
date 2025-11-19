"""add public flag to anonymous chats

Revision ID: b6f248c1b2a3
Revises: f9a8b7c6d5e4
Create Date: 2025-01-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6f248c1b2a3'
down_revision: Union[str, None] = 'f9a8b7c6d5e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет признак публичного чата и дату раскрытия."""

    op.add_column('anonymous_chats', sa.Column('is_public', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('anonymous_chats', sa.Column('revealed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Удаляет признак публичного чата и дату раскрытия."""

    op.drop_column('anonymous_chats', 'revealed_at')
    op.drop_column('anonymous_chats', 'is_public')

