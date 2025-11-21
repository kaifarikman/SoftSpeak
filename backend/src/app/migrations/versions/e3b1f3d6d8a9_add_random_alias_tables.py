"""add random alias tables and fields

Revision ID: e3b1f3d6d8a9
Revises: c7d8e9f0a1b2
Create Date: 2025-11-20 19:15:00.000000
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b1f3d6d8a9'
down_revision: str | Sequence[str] | None = 'c7d8e9f0a1b2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'random_name_adjectives',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('text', sa.String(length=128), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )
    op.create_table(
        'random_name_nouns',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('text', sa.String(length=128), nullable=False, unique=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
    )

    # add alias columns to anonymous chats
    op.add_column(
        'anonymous_chats',
        sa.Column('user1_alias', sa.String(length=128), nullable=False, server_default='Собеседник'),
    )
    op.add_column(
        'anonymous_chats',
        sa.Column('user2_alias', sa.String(length=128), nullable=False, server_default='Собеседник'),
    )
    op.alter_column('anonymous_chats', 'user1_alias', server_default=None)
    op.alter_column('anonymous_chats', 'user2_alias', server_default=None)

    # seed default words
    adjectives = [
        "Смелый",
        "Весёлый",
        "Таинственный",
        "Лучезарный",
        "Отважный",
        "Игривый",
        "Неожиданный",
        "Сияющий",
    ]
    nouns = [
        "Сокол",
        "Енот",
        "Феникс",
        "Лис",
        "Одуванчик",
        "Комета",
        "Тигр",
        "Кедр",
    ]
    adjective_table = sa.Table(
        'random_name_adjectives',
        sa.MetaData(),
        sa.Column('text', sa.String),
        sa.Column('is_active', sa.Boolean),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    noun_table = sa.Table(
        'random_name_nouns',
        sa.MetaData(),
        sa.Column('text', sa.String),
        sa.Column('is_active', sa.Boolean),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )
    now = datetime.now(timezone.utc)
    if adjectives:
        op.bulk_insert(
            adjective_table,
            [{'text': word, 'is_active': True, 'created_at': now, 'updated_at': now} for word in adjectives],
        )
    if nouns:
        op.bulk_insert(
            noun_table,
            [{'text': word, 'is_active': True, 'created_at': now, 'updated_at': now} for word in nouns],
        )


def downgrade() -> None:
    op.drop_column('anonymous_chats', 'user2_alias')
    op.drop_column('anonymous_chats', 'user1_alias')
    op.drop_table('random_name_nouns')
    op.drop_table('random_name_adjectives')

