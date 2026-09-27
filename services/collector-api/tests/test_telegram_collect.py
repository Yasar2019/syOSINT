from datetime import UTC, datetime, timedelta

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.orm import Session

from syosint.db import database
from syosint.models import IntakeItem, IntakeRevision, Source, TelegramCursor
from syosint.telegram_collect import ChannelPolicyError, resolve_public_channel, sync_channel
from syosint.telegram_types import ResolvedPublicChannel, TelegramMessage


NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


class FakeTransport:
    def __init__(self, messages=(), *, public=True, username="publicnews", failure=None, missing=()):
        self.entity = ResolvedPublicChannel(42, username, "Public News", public)
        self.messages = tuple(messages)
        self.failure = failure
        self.missing = set(missing)
        self.requests = []

    async def resolve_username(self, username):
        self.requests.append(("resolve", username))
        if self.failure:
            raise self.failure
        return self.entity

    async def iter_messages(self, channel_id, *, limit, since):
        self.requests.append(("iter", channel_id, limit, since))
        if self.failure:
            raise self.failure
        for item in self.messages[:limit]:
            if item.published_at >= since:
                yield item

    async def reconcile_messages(self, channel_id, native_ids):
        self.requests.append(("reconcile", channel_id, native_ids))
        return tuple(item for item in self.messages if str(item.message_id) in native_ids and item.message_id not in self.missing)


def message(number, *, text="Syria report", edited_at=None, published_at=None):
    return TelegramMessage(number, text, published_at or NOW - timedelta(hours=1), edited_at)


@pytest.fixture
def source(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'intake.sqlite'}")
    with Session(engine) as db:
        item = Source(name="Public News", url="https://t.me/publicnews", language="en",
                      kind="telegram", public_identifier="publicnews", enabled=True)
        db.add(item)
        db.flush()
        db.add(TelegramCursor(source_id=item.id, channel_id=42))
        db.commit()
        return engine, item.id


@pytest.mark.asyncio
async def test_rejects_private_and_mismatched_channel():
    with pytest.raises(ChannelPolicyError, match="public channel required"):
        await resolve_public_channel("publicnews", FakeTransport(public=False))
    with pytest.raises(ChannelPolicyError, match="username mismatch"):
        await resolve_public_channel("publicnews", FakeTransport(username="othername"))


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["https://t.me/publicnews", "@private", "ab", "a" * 33, "joinchat_code"])
async def test_rejects_non_username_references_before_transport(username):
    transport = FakeTransport()
    with pytest.raises(ChannelPolicyError):
        await resolve_public_channel(username, transport)
    assert transport.requests == []


@pytest.mark.asyncio
async def test_initial_sync_is_bounded_and_advances_cursor(source):
    engine, source_id = source
    posts = tuple(message(n) for n in range(1, 701)) + (message(900, published_at=NOW - timedelta(days=8)),)
    transport = FakeTransport(posts)
    summary = await sync_channel(engine, source_id, transport, NOW)
    with Session(engine) as db:
        rows = db.scalars(select(IntakeItem)).all()
        cursor = db.get(TelegramCursor, source_id)
        assert len(rows) == 500
        # SQLite round-trips timezone-aware columns as naive UTC datetimes.
        assert all(row.published_at >= (NOW - timedelta(days=7)).replace(tzinfo=None) for row in rows)
        assert cursor.last_message_id == 500
    assert summary.created == 500
    assert ("iter", 42, 500, NOW - timedelta(days=7)) in transport.requests


@pytest.mark.asyncio
async def test_edits_create_private_revisions_and_replays_do_not_duplicate(source):
    engine, source_id = source
    assert (await sync_channel(engine, source_id, FakeTransport([message(1)]), NOW)).created == 1
    changed = message(1, text="Corrected report", edited_at=NOW)
    assert (await sync_channel(engine, source_id, FakeTransport([changed]), NOW + timedelta(minutes=1))).created == 0
    await sync_channel(engine, source_id, FakeTransport([changed]), NOW + timedelta(minutes=2))
    with Session(engine) as db:
        rows = db.scalars(select(IntakeItem)).all()
        assert len(rows) == 1
        assert rows[0].text == "Corrected report"
        assert len(db.scalars(select(IntakeRevision)).all()) == 1


@pytest.mark.asyncio
async def test_failed_collection_does_not_advance_cursor(source):
    engine, source_id = source
    with pytest.raises(RuntimeError, match="offline"):
        await sync_channel(engine, source_id, FakeTransport(failure=RuntimeError("offline")), NOW)
    with Session(engine) as db:
        cursor = db.get(TelegramCursor, source_id)
        assert cursor is None or cursor.last_message_id is None
        assert db.scalars(select(IntakeItem)).all() == []


@pytest.mark.asyncio
async def test_changed_username_owner_is_rejected_before_collection(source):
    engine, source_id = source
    transport = FakeTransport([message(1)])
    transport.entity = ResolvedPublicChannel(99, "publicnews", "New Owner", True)
    with pytest.raises(ChannelPolicyError, match="channel identity changed"):
        await sync_channel(engine, source_id, transport, NOW)
    assert not any(request[0] == "iter" for request in transport.requests)
    with Session(engine) as db:
        assert db.scalars(select(IntakeItem)).all() == []
        assert db.get(TelegramCursor, source_id).last_message_id is None


@pytest.mark.asyncio
async def test_reconciliation_saves_an_edit_outside_latest_batch(source):
    engine, source_id = source
    await sync_channel(engine, source_id, FakeTransport([message(1)]), NOW)

    class ReconcileTransport(FakeTransport):
        async def reconcile_messages(self, channel_id, native_ids):
            return (message(1, text="Updated in older post", edited_at=NOW),)

    await sync_channel(engine, source_id, ReconcileTransport(), NOW + timedelta(minutes=10))
    with Session(engine) as db:
        assert db.scalar(select(IntakeItem)).text == "Updated in older post"
        assert len(db.scalars(select(IntakeRevision)).all()) == 1


@pytest.mark.asyncio
async def test_reconciliation_marks_confirmed_deletion(source):
    engine, source_id = source
    await sync_channel(engine, source_id, FakeTransport([message(1)]), NOW)
    await sync_channel(engine, source_id, FakeTransport(), NOW + timedelta(minutes=10))
    with Session(engine) as db:
        assert db.scalar(select(IntakeItem)).deleted_at is not None


def test_migration_refuses_to_erase_approved_channel_identity(source):
    engine, _ = source
    config = Config("services/collector-api/alembic.ini")
    config.set_main_option("sqlalchemy.url", str(engine.url))
    with pytest.raises(RuntimeError, match="approved Telegram channel identity"):
        command.downgrade(config, "0003")
    with Session(engine) as db:
        assert db.get(TelegramCursor, 1).channel_id == 42
