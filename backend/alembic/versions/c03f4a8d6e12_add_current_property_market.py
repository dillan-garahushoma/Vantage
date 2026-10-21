"""Current estate marketing workflow, independent of legacy listings/sales.

Revision ID: c03f4a8d6e12
Revises: b92e3f7c5d01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'c03f4a8d6e12'
down_revision = 'b92e3f7c5d01'
branch_labels = None
depends_on = None


def _ref(name, target, nullable=False):
    return sa.Column(name, sa.Integer(), sa.ForeignKey(target, ondelete='RESTRICT'), nullable=nullable)


def _time():
    return sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)


def upgrade():
    # New tables only. No backfill, deletion or new constraint on existing data.
    op.create_table('marketing_authorities',
        sa.Column('authority_id', sa.Integer(), primary_key=True),
        _ref('estate_id', 'estates.estate_id'), _ref('property_id', 'properties.unit_id'),
        _ref('representative_id', 'users.user_id'), _ref('verified_by', 'users.user_id'),
        sa.Column('verification_reference', sa.String(240), nullable=False), _time(),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        _ref('revoked_by', 'users.user_id', nullable=True))
    op.create_index('uq_marketing_authority_active_unit', 'marketing_authorities', ['estate_id', 'property_id'], unique=True,
                    postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_index('ix_marketing_authority_estate_representative', 'marketing_authorities', ['estate_id', 'representative_id'])
    op.create_table('marketing_requests',
        sa.Column('request_id', sa.Integer(), primary_key=True),
        _ref('estate_id', 'estates.estate_id'), _ref('property_id', 'properties.unit_id'),
        _ref('authority_id', 'marketing_authorities.authority_id'), _ref('requester_id', 'users.user_id'),
        sa.Column('purpose', sa.String(10), nullable=False),
        sa.Column('requested_price', sa.Numeric(12, 2), nullable=False), sa.Column('notes', sa.Text()),
        sa.Column('status', sa.String(16), nullable=False), _ref('agent_id', 'users.user_id', nullable=True),
        sa.Column('decision_reason', sa.Text()), _ref('decided_by', 'users.user_id', nullable=True), _time(),
        sa.Column('decided_at', sa.TIMESTAMP(timezone=True)),
        sa.CheckConstraint("purpose IN ('sale','rent')", name='ck_marketing_request_purpose'),
        sa.CheckConstraint("status IN ('pending','approved','rejected','listed','cancelled','fulfilled')", name='ck_marketing_request_status'),
        sa.CheckConstraint('requested_price > 0', name='ck_marketing_request_price'))
    op.create_index('uq_marketing_request_open_unit', 'marketing_requests', ['estate_id', 'property_id'], unique=True,
                    postgresql_where=sa.text("status IN ('pending','approved','listed')"))
    op.create_index('ix_marketing_request_estate_requester', 'marketing_requests', ['estate_id', 'requester_id', 'request_id'])
    op.create_index('ix_marketing_request_estate_agent', 'marketing_requests', ['estate_id', 'agent_id', 'request_id'])
    op.create_table('market_listings',
        sa.Column('listing_id', sa.Integer(), primary_key=True),
        _ref('estate_id', 'estates.estate_id'), _ref('property_id', 'properties.unit_id'),
        _ref('request_id', 'marketing_requests.request_id'), sa.Column('purpose', sa.String(10), nullable=False),
        sa.Column('title', sa.String(160), nullable=False), sa.Column('description', sa.Text(), nullable=False),
        sa.Column('asking_price', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(16), nullable=False), sa.Column('version', sa.Integer(), nullable=False), _time(),
        sa.Column('published_at', sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint('request_id', name='uq_market_listing_request'),
        sa.CheckConstraint("purpose IN ('sale','rent')", name='ck_market_listing_purpose'),
        sa.CheckConstraint("status IN ('draft','active','withdrawn','sold','let')", name='ck_market_listing_status'),
        sa.CheckConstraint('asking_price > 0 AND version > 0', name='ck_market_listing_price_version'))
    op.create_index('ix_market_listing_estate_status', 'market_listings', ['estate_id', 'status', 'listing_id'])
    op.create_table('listing_price_events',
        sa.Column('price_id', sa.Integer(), primary_key=True), _ref('estate_id', 'estates.estate_id'),
        _ref('listing_id', 'market_listings.listing_id'), sa.Column('old_price', sa.Numeric(12, 2)),
        sa.Column('new_price', sa.Numeric(12, 2), nullable=False), _ref('changed_by', 'users.user_id'),
        sa.Column('reason', sa.Text(), nullable=False), sa.Column('listing_version', sa.Integer(), nullable=False), _time(),
        sa.UniqueConstraint('listing_id', 'listing_version', name='uq_listing_price_version'),
        sa.CheckConstraint('new_price > 0 AND (old_price IS NULL OR old_price > 0)', name='ck_listing_price_positive'))
    op.create_index('ix_listing_price_estate_listing', 'listing_price_events', ['estate_id', 'listing_id', 'price_id'])
    op.create_table('market_transactions',
        sa.Column('transaction_id', sa.Integer(), primary_key=True),
        _ref('estate_id', 'estates.estate_id'), _ref('property_id', 'properties.unit_id'),
        _ref('listing_id', 'market_listings.listing_id'), sa.Column('purpose', sa.String(10), nullable=False),
        sa.Column('actual_amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('asking_price_at_completion', sa.Numeric(12, 2), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False), _ref('recorded_by', 'users.user_id'),
        sa.Column('reference', sa.String(240), nullable=False), _time(),
        sa.UniqueConstraint('listing_id', name='uq_market_transaction_listing'),
        sa.CheckConstraint("purpose IN ('sale','rent')", name='ck_market_transaction_purpose'),
        sa.CheckConstraint('actual_amount > 0 AND asking_price_at_completion > 0', name='ck_market_transaction_amount'))
    op.create_index('ix_market_transaction_estate_purpose', 'market_transactions', ['estate_id', 'purpose', 'transaction_id'])
    op.create_table('market_events',
        sa.Column('event_id', sa.Integer(), primary_key=True), _ref('estate_id', 'estates.estate_id'),
        sa.Column('entity_type', sa.String(20), nullable=False), sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(30), nullable=False), _ref('actor_id', 'users.user_id'),
        sa.Column('details', JSONB(), nullable=False), _time())
    op.create_index('ix_market_event_estate_entity', 'market_events', ['estate_id', 'entity_type', 'entity_id', 'event_id'])


def downgrade():
    for table in ('market_events', 'market_transactions', 'listing_price_events',
                  'market_listings', 'marketing_requests', 'marketing_authorities'):
        op.drop_table(table)
