"""rename username to nickname

Revision ID: rename_username_nickname
Revises: add_is_banned
Create Date: 2025-12-03 06:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rename_username_nickname'
down_revision: Union[str, None] = 'add_is_banned'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Переименовываем колонку username в nickname
    op.alter_column('users', 'username', new_column_name='nickname')
    
    # Переименовываем индекс
    op.drop_index('ix_users_username', table_name='users')
    op.create_index('ix_users_nickname', 'users', ['nickname'], unique=True)


def downgrade() -> None:
    # Переименовываем обратно nickname в username
    op.alter_column('users', 'nickname', new_column_name='username')
    
    # Переименовываем индекс обратно
    op.drop_index('ix_users_nickname', table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

