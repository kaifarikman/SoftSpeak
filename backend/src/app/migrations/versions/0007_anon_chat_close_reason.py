"""Add anonymous chat close reason

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "anonymous_chats",
        sa.Column("close_reason", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("anonymous_chats", "close_reason")
