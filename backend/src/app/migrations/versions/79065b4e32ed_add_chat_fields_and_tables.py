"""add_chat_fields_and_tables

Revision ID: 79065b4e32ed
Revises: 26248e243d5f
Create Date: 2025-11-14 23:59:14.306353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '79065b4e32ed'
down_revision: Union[str, Sequence[str], None] = '26248e243d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новые поля в таблицу users
    op.add_column('users', sa.Column('avatar', sa.String(length=512), nullable=True, server_default=''))
    op.add_column('users', sa.Column('anonym', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('ai_enabled', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('messengers_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('settings_enabled', sa.Boolean(), nullable=False, server_default='true'))
    
    # Создаем таблицу chats
    op.create_table('chats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chats_user_id'), 'chats', ['user_id'], unique=False)
    
    # Создаем таблицу messages
    op.create_table('messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_from_user', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_chat_id'), 'messages', ['chat_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем таблицы в обратном порядке
    op.drop_index(op.f('ix_messages_chat_id'), table_name='messages')
    op.drop_table('messages')
    op.drop_index(op.f('ix_chats_user_id'), table_name='chats')
    op.drop_table('chats')
    
    # Удаляем поля из таблицы users
    op.drop_column('users', 'settings_enabled')
    op.drop_column('users', 'messengers_enabled')
    op.drop_column('users', 'ai_enabled')
    op.drop_column('users', 'anonym')
    op.drop_column('users', 'avatar')
