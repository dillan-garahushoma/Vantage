"""Add private immutable investment snapshots, without altering existing rows.

Revision ID: a81d2e6b4c90
Revises: f1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'a81d2e6b4c90'
down_revision = 'f1a2b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    # New table only: no backfill or constraints on existing application data.
    op.create_table(
        'investment_scenarios',
        sa.Column('scenario_id', sa.Integer(), primary_key=True),
        sa.Column('estate_id', sa.Integer(), sa.ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('property_id', sa.Integer(), sa.ForeignKey('properties.unit_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('owner_id', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('revision_of', sa.Integer(), sa.ForeignKey('investment_scenarios.scenario_id', ondelete='RESTRICT'), nullable=True),
        sa.Column('formula_version', sa.String(40), nullable=False),
        sa.Column('assumptions', postgresql.JSONB(), nullable=False),
        sa.Column('result', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_investment_scenarios_estate_owner_created', 'investment_scenarios', ['estate_id', 'owner_id', 'created_at', 'scenario_id'])


def downgrade():
    # Explicit downgrade removes this feature's new table only.
    op.drop_index('ix_investment_scenarios_estate_owner_created', table_name='investment_scenarios')
    op.drop_table('investment_scenarios')
