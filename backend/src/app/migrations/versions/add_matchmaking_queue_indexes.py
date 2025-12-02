"""add matchmaking queue indexes

Revision ID: a1b2c3d4e5f6
Revises: 20251120_media
Create Date: 2025-11-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '20251120_media'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет индексы для оптимизации запросов к matchmaking_queue."""
    
    # Отдельный индекс на is_searching для быстрой фильтрации
    op.create_index(
        'ix_matchmaking_queue_is_searching', 
        'matchmaking_queue', 
        ['is_searching'], 
        unique=False
    )
    
    # Составной индекс на (is_searching, user_id) для оптимизации поиска матчей
    op.create_index(
        'ix_matchmaking_queue_searching_user', 
        'matchmaking_queue', 
        ['is_searching', 'user_id'], 
        unique=False
    )


def downgrade() -> None:
    """Удаляет созданные индексы."""
    
    op.drop_index('ix_matchmaking_queue_searching_user', table_name='matchmaking_queue')
    op.drop_index('ix_matchmaking_queue_is_searching', table_name='matchmaking_queue')

