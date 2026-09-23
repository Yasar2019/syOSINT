"""Initial private vault tables.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("sources", sa.Column("id", sa.Integer, primary_key=True), sa.Column("name", sa.String(250), nullable=False), sa.Column("url", sa.Text, nullable=False, unique=True), sa.Column("language", sa.String(10), nullable=False))
    op.create_table("incidents", sa.Column("id", sa.Integer, primary_key=True), sa.Column("fields", sa.JSON, nullable=False), sa.Column("state", sa.String(30), nullable=False), sa.Column("review", sa.JSON, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("evidence", sa.Column("id", sa.Integer, primary_key=True), sa.Column("incident_id", sa.Integer, sa.ForeignKey("incidents.id"), nullable=False), sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False), sa.Column("url", sa.Text, nullable=False), sa.Column("text", sa.Text, nullable=False), sa.Column("published_at", sa.String(40), nullable=False), sa.Column("digest", sa.String(64), nullable=False))
    op.create_table("audit", sa.Column("id", sa.Integer, primary_key=True), sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False), sa.Column("action", sa.String(60), nullable=False), sa.Column("entity", sa.String(40), nullable=False), sa.Column("entity_id", sa.Integer, nullable=False), sa.Column("before_hash", sa.String(64)), sa.Column("after_hash", sa.String(64)), sa.Column("reason", sa.Text))


def downgrade():
    op.drop_table("audit")
    op.drop_table("evidence")
    op.drop_table("incidents")
    op.drop_table("sources")
