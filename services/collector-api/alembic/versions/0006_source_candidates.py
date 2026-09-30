"""Private source candidates and append-only human reviews."""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('source_candidates',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('platform', sa.String(20), nullable=False),
        sa.Column('canonical_url', sa.Text(), nullable=False),
        sa.Column('name', sa.String(250), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('suggestion_reason', sa.String(1000), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('platform', 'canonical_url', name='uq_candidate_platform_url'))
    op.create_index('ix_source_candidates_status', 'source_candidates', ['status', 'id'])
    op.create_table('candidate_reviews',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('candidate_id', sa.Integer(), sa.ForeignKey('source_candidates.id'), nullable=False),
        sa.Column('decision', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(1000), nullable=False),
        sa.Column('checks', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_candidate_reviews_candidate_id', 'candidate_reviews', ['candidate_id'])


def downgrade():
    op.drop_table('candidate_reviews')
    op.drop_table('source_candidates')
