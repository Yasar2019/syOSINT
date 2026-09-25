"""Preserve RSS records in shared private intake tables.

Revision ID: 0003
Revises: 0002
"""

from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

ITEM_COLUMNS = (
    "id, source_id, fingerprint, native_id, headline, url, text, published_at, "
    "collected_at, raw_digest, status, incident_id"
)
QUARANTINE_COLUMNS = "id, source_id, reason, raw_digest, native_id, headline, created_at"


def create_items(*, shared):
    name = "intake_items" if shared else "feed_items"
    prefix = "intake" if shared else "feed"
    extra = [
        sa.Column("platform", sa.String(20), nullable=False, server_default="rss"),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ] if shared else []
    op.create_table(
        name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("native_id", sa.Text, nullable=True),
        sa.Column("headline", sa.Text, nullable=shared),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("incident_id", sa.Integer, sa.ForeignKey("incidents.id"), nullable=True),
        *extra,
        sa.UniqueConstraint("source_id", "fingerprint", name=f"uq_{prefix}_item_source_fingerprint"),
    )
    op.create_index(f"ix_{name}_source_id", name, ["source_id"])
    if shared:
        # Duplicate observations predate shared intake and retain their provenance.
        predicate = sa.text("native_id IS NOT NULL AND status != 'duplicate'")
        op.create_index(
            "uq_intake_item_source_native_id", name, ["source_id", "native_id"],
            unique=True, sqlite_where=predicate, postgresql_where=predicate,
        )


def create_quarantine(*, shared):
    prefix = "intake" if shared else "feed"
    name = f"{prefix}_quarantine"
    extra = [sa.Column("platform", sa.String(20), nullable=False, server_default="rss")] if shared else []
    op.create_table(
        name,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False),
        sa.Column("native_id", sa.Text, nullable=True),
        sa.Column("headline", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        *extra,
        sa.UniqueConstraint("source_id", "raw_digest", "reason", name=f"uq_{prefix}_quarantine_source_digest_reason"),
    )
    op.create_index(f"ix_{name}_source_id", name, ["source_id"])


def upgrade():
    with op.batch_alter_table("sources") as batch:
        batch.add_column(sa.Column("public_identifier", sa.Text, nullable=True))
        batch.add_column(sa.Column("review_notes", sa.Text, nullable=True))
        batch.add_column(sa.Column("media_enabled", sa.Boolean, nullable=False, server_default=sa.false()))

    create_items(shared=True)
    create_quarantine(shared=True)
    op.execute(sa.text(f"INSERT INTO intake_items ({ITEM_COLUMNS}, platform) SELECT {ITEM_COLUMNS}, 'rss' FROM feed_items"))
    op.execute(sa.text(f"INSERT INTO intake_quarantine ({QUARANTINE_COLUMNS}, platform) SELECT {QUARANTINE_COLUMNS}, 'rss' FROM feed_quarantine"))

    op.create_table(
        "intake_revisions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("intake_items.id"), nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("raw_digest", sa.String(64), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_intake_revisions_item_id", "intake_revisions", ["item_id"])
    op.create_table(
        "telegram_cursors",
        sa.Column("source_id", sa.Integer, sa.ForeignKey("sources.id"), primary_key=True),
        sa.Column("last_message_id", sa.Integer, nullable=True),
        sa.Column("reconcile_from_id", sa.Integer, nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_poll_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rate_limit_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consecutive_failures", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_status", sa.String(20), nullable=True),
        sa.Column("last_error_category", sa.Text, nullable=True),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("item_id", sa.Integer, sa.ForeignKey("intake_items.id"), nullable=False),
        sa.Column("local_path", sa.Text, nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer, nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_media_assets_item_id", "media_assets", ["item_id"])
    op.drop_table("feed_quarantine")
    op.drop_table("feed_items")


def downgrade():
    # Check before any DDL: SQLite cannot roll back all schema operations.
    connection = op.get_bind()
    checks = (
        "SELECT 1 FROM sources WHERE kind='telegram' OR public_identifier IS NOT NULL OR review_notes IS NOT NULL OR media_enabled=true LIMIT 1",
        "SELECT 1 FROM intake_items WHERE platform!='rss' OR edited_at IS NOT NULL OR deleted_at IS NOT NULL OR headline IS NULL LIMIT 1",
        "SELECT 1 FROM intake_quarantine WHERE platform!='rss' LIMIT 1",
        "SELECT 1 FROM intake_revisions LIMIT 1",
        "SELECT 1 FROM telegram_cursors LIMIT 1",
        "SELECT 1 FROM media_assets LIMIT 1",
    )
    if any(connection.scalar(sa.text(query)) is not None for query in checks):
        raise RuntimeError("Cannot downgrade: shared intake data would be lost; retain revision 0003 or restore an earlier backup")

    create_items(shared=False)
    create_quarantine(shared=False)
    op.execute(sa.text(f"INSERT INTO feed_items ({ITEM_COLUMNS}) SELECT {ITEM_COLUMNS} FROM intake_items"))
    op.execute(sa.text(f"INSERT INTO feed_quarantine ({QUARANTINE_COLUMNS}) SELECT {QUARANTINE_COLUMNS} FROM intake_quarantine"))
    op.drop_table("media_assets")
    op.drop_table("telegram_cursors")
    op.drop_table("intake_revisions")
    op.drop_table("intake_quarantine")
    op.drop_table("intake_items")
    with op.batch_alter_table("sources") as batch:
        batch.drop_column("media_enabled")
        batch.drop_column("review_notes")
        batch.drop_column("public_identifier")
