"""Add media fields to anonymous messages."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251120_media'
down_revision = 'e3b1f3d6d8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('anonymous_messages', sa.Column('media_type', sa.String(length=16), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_url', sa.String(length=512), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_preview_url', sa.String(length=512), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_size', sa.Integer(), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_duration', sa.Float(), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_width', sa.Integer(), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_height', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('anonymous_messages', 'media_height')
    op.drop_column('anonymous_messages', 'media_width')
    op.drop_column('anonymous_messages', 'media_duration')
    op.drop_column('anonymous_messages', 'media_size')
    op.drop_column('anonymous_messages', 'media_preview_url')
    op.drop_column('anonymous_messages', 'media_url')
    op.drop_column('anonymous_messages', 'media_type')

