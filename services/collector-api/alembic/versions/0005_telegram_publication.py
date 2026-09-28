"""Store sanitized editorial drafts and approved Telegram leads.

Revision ID: 0005
Revises: 0004
"""

from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "telegram_publication_previews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("intake_items.id"), nullable=False),
        sa.Column("draft_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("record", sa.JSON, nullable=False),
        sa.Column("safety", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "telegram_publications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("intake_items.id"), nullable=False, unique=True),
        sa.Column("public_id", sa.String(120), nullable=False, unique=True),
        sa.Column("source_digest", sa.String(64), nullable=False),
        sa.Column("record", sa.JSON, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "telegram_publication_revisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("publication_id", sa.Integer, sa.ForeignKey("telegram_publications.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("reason_en", sa.Text, nullable=False),
        sa.Column("reason_ar", sa.Text, nullable=False),
        sa.Column("previous_headline_en", sa.Text, nullable=True),
        sa.Column("previous_headline_ar", sa.Text, nullable=True),
        sa.Column("revised_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_telegram_publication_revisions_publication_id", "telegram_publication_revisions", ["publication_id"])


def downgrade():
    bound = op.get_bind()
    for table in ("telegram_publication_revisions", "telegram_publications", "telegram_publication_previews"):
        if bound.scalar(sa.text(f"SELECT COUNT(*) FROM {table}")):
            raise RuntimeError("cannot discard Telegram editorial publication history")
    op.drop_index("ix_telegram_publication_revisions_publication_id", table_name="telegram_publication_revisions")
    op.drop_table("telegram_publication_revisions")
    op.drop_table("telegram_publications")
    op.drop_table("telegram_publication_previews")
