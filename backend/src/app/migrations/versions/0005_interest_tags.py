"""Add interest tags

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "interest_tags",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("emoji", sa.String(length=8), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_interest_tags_name"),
    )
    op.create_table(
        "user_interest_tags",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["interest_tags.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "tag_id"),
    )
    op.execute(
        """
        INSERT INTO interest_tags (name, emoji) VALUES
        ('Психология', '🧠'),
        ('Спорт', '⚽'),
        ('Кино', '🎬'),
        ('Музыка', '🎵'),
        ('Технологии', '💻'),
        ('Путешествия', '✈️'),
        ('Книги', '📚'),
        ('Игры', '🎮')
        """
    )


def downgrade() -> None:
    op.drop_table("user_interest_tags")
    op.drop_table("interest_tags")
