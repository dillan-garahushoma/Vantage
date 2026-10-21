"""Add operational intelligence history; no existing rows or constraints change.

Revision ID: b92e3f7c5d01
Revises: a81d2e6b4c90
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'b92e3f7c5d01'
down_revision = 'a81d2e6b4c90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'intelligence_briefings',
        sa.Column('briefing_id', sa.Integer(), primary_key=True),
        sa.Column('estate_id', sa.Integer(), sa.ForeignKey('estates.estate_id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True),
        sa.Column('template_version', sa.String(40), nullable=False),
        sa.Column('data_origin', sa.String(10), nullable=False),
        sa.Column('facts', postgresql.JSONB(), nullable=False),
        sa.Column('output', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_intelligence_briefings_estate_created', 'intelligence_briefings',
                    ['estate_id', 'created_at', 'briefing_id'])


def downgrade():
    op.drop_index('ix_intelligence_briefings_estate_created', table_name='intelligence_briefings')
    op.drop_table('intelligence_briefings')
