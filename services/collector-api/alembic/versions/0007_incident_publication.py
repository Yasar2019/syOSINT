"""Private incident publication snapshots and drafts."""
from alembic import op
import sqlalchemy as sa
revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('incident_publications', sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id'), primary_key=True), sa.Column('version', sa.Integer(), nullable=False), sa.Column('record', sa.JSON(), nullable=False), sa.CheckConstraint('version >= 1'))
    op.create_table('incident_publication_revisions', sa.Column('id', sa.Integer(), primary_key=True), sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id'), nullable=False), sa.Column('version', sa.Integer(), nullable=False), sa.Column('record', sa.JSON(), nullable=False), sa.Column('action', sa.String(20), nullable=False), sa.Column('reason_en', sa.Text(), nullable=False), sa.Column('reason_ar', sa.Text(), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint('incident_id','version'), sa.CheckConstraint('version >= 1'))
    op.create_table('incident_correction_drafts', sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id'), primary_key=True), sa.Column('base_version', sa.Integer(), nullable=False), sa.Column('fields', sa.JSON(), nullable=False), sa.Column('review', sa.JSON(), nullable=False), sa.Column('reason_en', sa.Text(), nullable=False), sa.Column('reason_ar', sa.Text(), nullable=False), sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('incident_withdrawal_previews', sa.Column('incident_id', sa.Integer(), sa.ForeignKey('incidents.id'), primary_key=True), sa.Column('base_version', sa.Integer(), nullable=False), sa.Column('preview_hash', sa.String(64), nullable=False), sa.Column('record', sa.JSON(), nullable=False), sa.Column('reason_en', sa.Text(), nullable=False), sa.Column('reason_ar', sa.Text(), nullable=False), sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    for table in ('incident_withdrawal_previews','incident_correction_drafts','incident_publication_revisions','incident_publications'):
        op.drop_table(table)
