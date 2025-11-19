"""add reveal confirmation fields

Revision ID: c7d8e9f0a1b2
Revises: b6f248c1b2a3
Create Date: 2025-01-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = 'b6f248c1b2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет поля для двухстороннего подтверждения раскрытия личности."""

    op.add_column('anonymous_chats', sa.Column('user1_revealed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('anonymous_chats', sa.Column('user2_revealed', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Удаляет поля для двухстороннего подтверждения раскрытия личности."""

    op.drop_column('anonymous_chats', 'user2_revealed')
    op.drop_column('anonymous_chats', 'user1_revealed')


