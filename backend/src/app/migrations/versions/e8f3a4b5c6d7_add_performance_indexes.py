"""add performance indexes

Revision ID: e8f3a4b5c6d7
Revises: d70d47ba25a5
Create Date: 2024-11-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e8f3a4b5c6d7'
down_revision: Union[str, None] = 'd70d47ba25a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет индексы для улучшения производительности запросов."""
    
    # Индексы для user_answers (для быстрого получения ответов пользователя)
    op.create_index(
        'ix_user_answers_user_id_created', 
        'user_answers', 
        ['user_id', 'created_at'], 
        unique=False
    )
    
    # Индексы для questions (для быстрого получения активных вопросов по категории)
    op.create_index(
        'ix_questions_category_active', 
        'questions', 
        ['category_id', 'is_active', 'order'], 
        unique=False
    )
    
    # Индексы для messages (для быстрого получения сообщений чата)
    op.create_index(
        'ix_messages_chat_created', 
        'messages', 
        ['chat_id', 'created_at'], 
        unique=False
    )
    
    # Индексы для anonymous_messages
    op.create_index(
        'ix_anonymous_messages_chat_created', 
        'anonymous_messages', 
        ['chat_id', 'created_at'], 
        unique=False
    )
    op.create_index(
        'ix_anonymous_messages_sender', 
        'anonymous_messages', 
        ['sender_id', 'created_at'], 
        unique=False
    )
    
    # Composite индексы для anonymous_chats (для быстрого поиска активных чатов)
    op.create_index(
        'ix_anonymous_chats_user1_active', 
        'anonymous_chats', 
        ['user1_id', 'is_active', 'updated_at'], 
        unique=False
    )
    op.create_index(
        'ix_anonymous_chats_user2_active', 
        'anonymous_chats', 
        ['user2_id', 'is_active', 'updated_at'], 
        unique=False
    )
    
    # Индекс для matchmaking_queue (для быстрого поиска ожидающих пользователей)
    op.create_index(
        'ix_matchmaking_queue_searching', 
        'matchmaking_queue', 
        ['is_searching', 'joined_at'], 
        unique=False
    )


def downgrade() -> None:
    """Удаляет созданные индексы."""
    
    op.drop_index('ix_matchmaking_queue_searching', table_name='matchmaking_queue')
    op.drop_index('ix_anonymous_chats_user2_active', table_name='anonymous_chats')
    op.drop_index('ix_anonymous_chats_user1_active', table_name='anonymous_chats')
    op.drop_index('ix_anonymous_messages_sender', table_name='anonymous_messages')
    op.drop_index('ix_anonymous_messages_chat_created', table_name='anonymous_messages')
    op.drop_index('ix_messages_chat_created', table_name='messages')
    op.drop_index('ix_questions_category_active', table_name='questions')
    op.drop_index('ix_user_answers_user_id_created', table_name='user_answers')

