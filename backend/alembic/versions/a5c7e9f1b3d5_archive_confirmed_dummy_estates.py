"""Archive the five estates the owner confirmed are dummy data on 25 October.

Restore the sample classification reversed by f3a6b2c9d1e4. Keep every operational
row and the exact previous flags so this correction is reversible.
"""
from alembic import op
import sqlalchemy as sa

revision = 'a5c7e9f1b3d5'
down_revision = 'b4d2c6e8f1a0'
branch_labels = None
depends_on = None

_BACKUP_TABLE = 'migration_a5c7e9f1b3d5_estate_flags'
_NAMES = ('Eastbank Court', 'Lakeside Gardens', 'Quarry View Flats', 'Silverleaf Reserve', 'Willowbrook Mews')
_NAME_LIST = ', '.join(repr(name) for name in _NAMES)


def upgrade() -> None:
    op.create_table(
        _BACKUP_TABLE,
        sa.Column('estate_id', sa.Integer(), primary_key=True),
        sa.Column('is_demo', sa.Boolean(), nullable=False),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('show_living_score', sa.Boolean(), nullable=False),
    )
    op.execute(
        f'INSERT INTO {_BACKUP_TABLE} (estate_id, is_demo, is_public, show_living_score) '
        f'SELECT estate_id, is_demo, is_public, show_living_score FROM estates WHERE name IN ({_NAME_LIST})'
    )
    op.execute(
        'UPDATE estates SET is_demo = true, is_public = false, show_living_score = false '
        f'WHERE estate_id IN (SELECT estate_id FROM {_BACKUP_TABLE})'
    )


def downgrade() -> None:
    op.execute(
        'UPDATE estates AS estate SET is_demo = prior.is_demo, is_public = prior.is_public, '
        f'show_living_score = prior.show_living_score FROM {_BACKUP_TABLE} AS prior '
        'WHERE estate.estate_id = prior.estate_id'
    )
    op.drop_table(_BACKUP_TABLE)
