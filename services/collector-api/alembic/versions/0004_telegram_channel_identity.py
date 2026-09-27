"""Bind approved public usernames to immutable Telegram channel identity.

Revision ID: 0004
Revises: 0003
"""

from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("telegram_cursors", sa.Column("channel_id", sa.BigInteger(), nullable=True))


def downgrade():
    bound = op.get_bind()
    if bound.scalar(sa.text("SELECT COUNT(*) FROM telegram_cursors WHERE channel_id IS NOT NULL")):
        raise RuntimeError("cannot drop approved Telegram channel identity")
    op.drop_column("telegram_cursors", "channel_id")
