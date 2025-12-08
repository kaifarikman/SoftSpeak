"""Drop blacklist table

Revision ID: drop_blacklist_table
Revises: add_created_at_verification
Create Date: 2025-12-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'drop_blacklist_table'
down_revision = 'add_created_at_verification'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Удаляем таблицу blacklist
    op.drop_index(op.f('ix_blacklist_blocked_user_id'), table_name='blacklist')
    op.drop_index(op.f('ix_blacklist_user_id'), table_name='blacklist')
    op.drop_table('blacklist')


def downgrade() -> None:
    # Восстанавливаем таблицу blacklist
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

