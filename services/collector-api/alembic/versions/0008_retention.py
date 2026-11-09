"""Private retention holds and aggregate run history."""
from alembic import op
import sqlalchemy as sa
revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade():
    # Retention audit/hold references must never alias a later unrelated row.
    # SQLite AUTOINCREMENT preserves a monotonically increasing identity highwater.
    for table in ('intake_items', 'intake_revisions', 'media_assets', 'intake_quarantine', 'telegram_publication_previews'):
        with op.batch_alter_table(table, recreate='always', table_kwargs={'sqlite_autoincrement': True}):
            pass
    op.create_table('retention_holds', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('target_kind', sa.String(20), nullable=False), sa.Column('target_id', sa.Integer(), nullable=False), sa.Column('reason', sa.String(1000), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.Column('released_at', sa.DateTime(timezone=True)))
    op.create_index('uq_active_retention_hold', 'retention_holds', ['target_kind', 'target_id'], unique=True, sqlite_where=sa.text('released_at IS NULL'), postgresql_where=sa.text('released_at IS NULL'))
    op.create_table('retention_runs', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False), sa.Column('dry_run', sa.Boolean(), nullable=False), sa.Column('counts', sa.JSON(), nullable=False), sa.Column('status', sa.String(20), nullable=False))


def downgrade():
    op.drop_table('retention_runs')
    op.drop_table('retention_holds')
