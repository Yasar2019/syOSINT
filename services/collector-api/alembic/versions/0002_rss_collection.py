"""Add private RSS collection tables.

Revision ID: 0002
Revises: 0001
"""

from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("sources") as batch:
        batch.add_column(
            sa.Column("kind", sa.String(20), nullable=False, server_default="manual")
        )
        batch.add_column(sa.Column("feed_url", sa.Text, nullable=True))
        batch.add_column(
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true())
        )
        batch.add_column(
            sa.Column(
                "poll_interval_minutes",
                sa.Integer,
                nullable=False,
                server_default="30",
            )
        )

    op.create_table(
        "feed_items",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("native_id", sa.Text, nullable=True),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("incident_id", sa.Integer, sa.ForeignKey("incidents.id"), nullable=True),
        sa.UniqueConstraint(
            "source_id", "fingerprint", name="uq_feed_item_source_fingerprint"
        ),
    )
    op.create_index("ix_feed_items_source_id", "feed_items", ["source_id"])
    op.create_table(
        "feed_cursors",
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), primary_key=True),
        sa.Column("etag", sa.Text, nullable=True),
        sa.Column("last_modified", sa.Text, nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_status", sa.String(20), nullable=True),
        sa.Column("last_error_category", sa.Text, nullable=True),
    )
    op.create_table(
        "feed_quarantine",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False),
        sa.Column("native_id", sa.Text, nullable=True),
        sa.Column("headline", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source_id",
            "raw_digest",
            "reason",
            name="uq_feed_quarantine_source_digest_reason",
        ),
    )
    op.create_index(
        "ix_feed_quarantine_source_id", "feed_quarantine", ["source_id"]
    )


def downgrade():
    op.drop_index("ix_feed_quarantine_source_id", table_name="feed_quarantine")
    op.drop_table("feed_quarantine")
    op.drop_table("feed_cursors")
    op.drop_index("ix_feed_items_source_id", table_name="feed_items")
    op.drop_table("feed_items")
    with op.batch_alter_table("sources") as batch:
        batch.drop_column("poll_interval_minutes")
        batch.drop_column("enabled")
        batch.drop_column("feed_url")
        batch.drop_column("kind")
