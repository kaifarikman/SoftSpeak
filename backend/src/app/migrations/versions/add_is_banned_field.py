"""add is_banned field

Revision ID: add_is_banned
Revises: add_reports_system
Create Date: 2025-12-03 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_is_banned'
down_revision: Union[str, None] = 'add_reports_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем колонку is_banned
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'))
    
    # Переносим существующие баны из is_active в is_banned
    # Пользователи с is_active = false и email != NULL были забанены
    op.execute("""
        UPDATE users 
        SET is_banned = true 
        WHERE is_active = false AND email IS NOT NULL
    """)
    
    # Восстанавливаем is_active = true для забаненных пользователей
    # (они были активны до бана, is_active использовался для бана ошибочно)
    op.execute("""
        UPDATE users 
        SET is_active = true 
        WHERE is_banned = true
    """)


def downgrade() -> None:
    # При откате переносим баны обратно в is_active
    op.execute("""
        UPDATE users 
        SET is_active = false 
        WHERE is_banned = true
    """)
    
    # Удаляем колонку is_banned
    op.drop_column('users', 'is_banned')

