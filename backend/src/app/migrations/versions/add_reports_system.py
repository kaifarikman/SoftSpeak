from alembic import op
import sqlalchemy as sa

revision = 'add_reports_system'
down_revision = 'remove_media_fields'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('users', sa.Column('reports_count', sa.Integer(), nullable=False, server_default='0'))
    
    op.add_column('anonymous_chats', sa.Column('is_blocked', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('anonymous_chats', sa.Column('blocked_by_report_id', sa.Integer(), nullable=True))
    
    op.create_table(
        'reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reporter_id', sa.Integer(), nullable=False),
        sa.Column('reported_user_id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_by_admin_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reported_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['chat_id'], ['anonymous_chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resolved_by_admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_reports_reported_user_id'), 'reports', ['reported_user_id'], unique=False)
    op.create_index(op.f('ix_reports_chat_id'), 'reports', ['chat_id'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_foreign_key(
        'fk_anonymous_chats_blocked_by_report',
        'anonymous_chats',
        'reports',
        ['blocked_by_report_id'],
        ['id'],
        ondelete='SET NULL'
    )

def downgrade() -> None:
    op.drop_constraint('fk_anonymous_chats_blocked_by_report', 'anonymous_chats', type_='foreignkey')
    op.drop_index(op.f('ix_reports_status'), table_name='reports')
    op.drop_index(op.f('ix_reports_chat_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_reported_user_id'), table_name='reports')
    op.drop_index(op.f('ix_reports_reporter_id'), table_name='reports')
    op.drop_table('reports')
    op.drop_column('anonymous_chats', 'blocked_by_report_id')
    op.drop_column('anonymous_chats', 'is_blocked')
    op.drop_column('users', 'reports_count')

