from alembic import op
import sqlalchemy as sa

revision = 'remove_media_fields'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('anonymous_messages', 'media_height')
    op.drop_column('anonymous_messages', 'media_width')
    op.drop_column('anonymous_messages', 'media_duration')
    op.drop_column('anonymous_messages', 'media_size')
    op.drop_column('anonymous_messages', 'media_preview_url')
    op.drop_column('anonymous_messages', 'media_url')
    op.drop_column('anonymous_messages', 'media_type')
    op.drop_column('users', 'media_auto_upload_videos')
    op.drop_column('users', 'media_auto_upload_photos')
    op.drop_column('users', 'avatar')

def downgrade() -> None:
    op.add_column('anonymous_messages', sa.Column('media_type', sa.String(length=16), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_url', sa.String(length=512), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_preview_url', sa.String(length=512), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_size', sa.Integer(), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_duration', sa.Float(), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_width', sa.Integer(), nullable=True))
    op.add_column('anonymous_messages', sa.Column('media_height', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('media_auto_upload_photos', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('media_auto_upload_videos', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('avatar', sa.String(length=512), nullable=True))

