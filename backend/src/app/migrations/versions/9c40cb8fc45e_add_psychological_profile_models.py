"""add_psychological_profile_models

Revision ID: 9c40cb8fc45e
Revises: 79065b4e32ed
Create Date: 2025-11-15 00:36:40.299716

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c40cb8fc45e'
down_revision: Union[str, Sequence[str], None] = '79065b4e32ed'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаем таблицу categories
    op.create_table('categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Создаем таблицу questions
    op.create_table('questions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_questions_category_id'), 'questions', ['category_id'], unique=False)
    
    # Создаем таблицу user_answers
    op.create_table('user_answers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('answer_text', sa.Text(), nullable=False),
        sa.Column('embedding', sa.ARRAY(sa.Float()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_answers_question_id'), 'user_answers', ['question_id'], unique=False)
    op.create_index(op.f('ix_user_answers_user_id'), 'user_answers', ['user_id'], unique=False)
    
    # Создаем таблицу psychological_profiles
    op.create_table('psychological_profiles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('profile_vector', sa.ARRAY(sa.Float()), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_psychological_profiles_user_id'), 'psychological_profiles', ['user_id'], unique=False)
    
    # Создаем 10 базовых категорий
    categories_table = sa.table('categories',
        sa.column('id', sa.Integer),
        sa.column('name', sa.String),
        sa.column('description', sa.Text),
        sa.column('order', sa.Integer)
    )
    
    op.bulk_insert(categories_table, [
        {'name': 'Личность и характер', 'description': 'Вопросы о личностных качествах и характере', 'order': 1},
        {'name': 'Интересы и хобби', 'description': 'Вопросы об увлечениях и интересах', 'order': 2},
        {'name': 'Ценности и убеждения', 'description': 'Вопросы о жизненных ценностях и убеждениях', 'order': 3},
        {'name': 'Общение и отношения', 'description': 'Вопросы о стиле общения и отношениях с людьми', 'order': 4},
        {'name': 'Работа и карьера', 'description': 'Вопросы о профессиональной деятельности', 'order': 5},
        {'name': 'Эмоции и чувства', 'description': 'Вопросы об эмоциональном состоянии', 'order': 6},
        {'name': 'Жизненные цели', 'description': 'Вопросы о планах и целях в жизни', 'order': 7},
        {'name': 'Отдых и развлечения', 'description': 'Вопросы о способах отдыха и развлечений', 'order': 8},
        {'name': 'Семья и близкие', 'description': 'Вопросы о семье и близких людях', 'order': 9},
        {'name': 'Саморазвитие', 'description': 'Вопросы о личностном росте и развитии', 'order': 10},
    ])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_psychological_profiles_user_id'), table_name='psychological_profiles')
    op.drop_table('psychological_profiles')
    op.drop_index(op.f('ix_user_answers_user_id'), table_name='user_answers')
    op.drop_index(op.f('ix_user_answers_question_id'), table_name='user_answers')
    op.drop_table('user_answers')
    op.drop_index(op.f('ix_questions_category_id'), table_name='questions')
    op.drop_table('questions')
    op.drop_table('categories')
