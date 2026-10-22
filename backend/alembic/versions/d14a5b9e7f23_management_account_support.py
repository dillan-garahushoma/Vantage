"""Management account support and repeat repair cycles; historical data retained."""
from alembic import op
import sqlalchemy as sa

revision = 'd14a5b9e7f23'
down_revision = 'c03f4a8d6e12'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('auth_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('password_changed_at', sa.TIMESTAMP(timezone=True)))
    op.create_table('account_preferences',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('maintenance_notifications', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    op.create_table('recovery_grants',
        sa.Column('grant_id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_digest', sa.String(64), nullable=False, unique=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(timezone=True)))
    op.create_index('ix_recovery_grants_user_id', 'recovery_grants', ['user_id'])
    op.create_table('operational_notifications',
        sa.Column('notification_id', sa.Integer(), primary_key=True),
        sa.Column('estate_id', sa.Integer(), sa.ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('kind', sa.String(40), nullable=False),
        sa.Column('resource_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('read_at', sa.TIMESTAMP(timezone=True)))
    op.create_index('ix_notifications_estate_user_id', 'operational_notifications',
                    ['estate_id', 'user_id', 'notification_id'])
    # The previous stronger index guarantees this weaker constraint is safe.
    op.drop_index('uq_active_work_order_per_complaint', table_name='maintenance_work_orders')
    op.create_index('uq_active_work_order_per_complaint', 'maintenance_work_orders',
        ['complaint_id'], unique=True, postgresql_where=sa.text("status IN ('assigned', 'in_progress')"))


def downgrade():
    # Never delete repeat repair history to restore the old index.
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT complaint_id FROM maintenance_work_orders
                   WHERE status <> 'cancelled' GROUP BY complaint_id HAVING count(*) > 1) THEN
            RAISE EXCEPTION 'Cannot downgrade: repeated repair history violates the previous work-order index. Archive/reconcile explicitly before downgrade; no rows were deleted.';
        END IF;
    END $$;""")
    op.drop_index('uq_active_work_order_per_complaint', table_name='maintenance_work_orders')
    op.create_index('uq_active_work_order_per_complaint', 'maintenance_work_orders',
        ['complaint_id'], unique=True, postgresql_where=sa.text("status <> 'cancelled'"))
    op.drop_index('ix_notifications_estate_user_id', table_name='operational_notifications')
    op.drop_table('operational_notifications')
    op.drop_index('ix_recovery_grants_user_id', table_name='recovery_grants')
    op.drop_table('recovery_grants')
    op.drop_table('account_preferences')
    op.drop_column('users', 'password_changed_at')
    op.drop_column('users', 'auth_version')
