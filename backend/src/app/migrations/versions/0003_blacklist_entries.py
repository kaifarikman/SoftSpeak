"""Add blacklist entries

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "blacklist_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("blocked_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["blocked_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "blocked_user_id", name="uq_blacklist_pair"),
    )
    op.create_index("ix_blacklist_entries_user_id", "blacklist_entries", ["user_id"])
    op.create_index(
        "ix_blacklist_entries_blocked_user_id",
        "blacklist_entries",
        ["blocked_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_blacklist_entries_blocked_user_id", table_name="blacklist_entries")
    op.drop_index("ix_blacklist_entries_user_id", table_name="blacklist_entries")
    op.drop_table("blacklist_entries")
