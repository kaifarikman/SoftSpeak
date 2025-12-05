"""Add created_at to email_verification_codes

Revision ID: add_created_at_verification
Revises: add_is_banned_field
Create Date: 2025-12-05

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


# revision identifiers, used by Alembic.
revision = 'add_created_at_verification'
down_revision = 'rename_username_nickname'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем колонку created_at с дефолтным значением текущего времени
    op.add_column(
        'email_verification_codes',
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now()
        )
    )


def downgrade() -> None:
    op.drop_column('email_verification_codes', 'created_at')

