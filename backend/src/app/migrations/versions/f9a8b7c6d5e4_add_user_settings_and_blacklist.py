"""add user settings and blacklist

Revision ID: f9a8b7c6d5e4
Revises: e8f3a4b5c6d7
Create Date: 2024-11-17 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f9a8b7c6d5e4'
down_revision: Union[str, None] = 'e8f3a4b5c6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет поля настроек в users и создает таблицу blacklist."""
    
    # Добавляем поля настроек в таблицу users
    op.add_column('users', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('notification_anon_chats', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('notification_open_chats', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('users', sa.Column('media_auto_upload_photos', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('media_auto_upload_videos', sa.Boolean(), nullable=False, server_default='false'))
    
    # Создаем таблицу blacklist
    op.create_table(
        'blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('blocked_user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['blocked_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'blocked_user_id', name='uq_blacklist_user_blocked')
    )
    op.create_index(op.f('ix_blacklist_user_id'), 'blacklist', ['user_id'], unique=False)
    op.create_index(op.f('ix_blacklist_blocked_user_id'), 'blacklist', ['blocked_user_id'], unique=False)


def downgrade() -> None:
    """Удаляет поля настроек и таблицу blacklist."""
    
    op.drop_index(op.f('ix_blacklist_blocked_user_id'), table_name='blacklist')
    op.drop_index(op.f('ix_blacklist_user_id'), table_name='blacklist')
    op.drop_table('blacklist')
    
    op.drop_column('users', 'media_auto_upload_videos')
    op.drop_column('users', 'media_auto_upload_photos')
    op.drop_column('users', 'notification_open_chats')
    op.drop_column('users', 'notification_anon_chats')
    op.drop_column('users', 'bio')

