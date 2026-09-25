from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256

import pytest
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syosint.db import database, record
from syosint.models import (
    Audit, Evidence, Incident, IntakeItem, IntakeQuarantine, IntakeRevision, Source, TelegramCursor,
)


NOW = datetime(2026, 9, 24, 12, tzinfo=UTC)
LATER = NOW + timedelta(minutes=30)


@pytest.fixture
def db(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def source(db):
    row = Source(name="Synthetic channel", url="https://t.me/example_channel",
                 language="en", kind="telegram")
    db.add(row)
    db.commit()
    return row


def normalized(native_id="42", text="original", edited_at=None):
    from syosint.intake_types import NormalizedIntakeItem

    return NormalizedIntakeItem(
        platform="telegram", native_id=native_id, headline=None,
        url=f"https://t.me/example_channel/{native_id}", text=text,
        published_at=NOW, edited_at=edited_at, collected_at=NOW,
        fingerprint=f"message-{native_id}", raw_digest=sha256(text.encode()).hexdigest(),
    )


def test_duplicate_native_id_with_new_digest_creates_revision(db, source):
    from syosint.intake_store import store_intake_batch

    first = normalized()
    edited = replace(normalized(text="corrected", edited_at=LATER),
                     collected_at=LATER, fingerprint="changed-fingerprint")
    store_intake_batch(db, source, (first,), (), None, NOW)
    item = db.scalar(select(IntakeItem))
    incident = Incident(fields={"title_en": "Analyst case"}, state="triage")
    db.add(incident)
    db.flush()
    item.incident_id = incident.id
    item.status = "attached"
    db.add(Evidence(incident_id=incident.id, source_id=source.id, url=item.url,
                    text="original", published_at=NOW.isoformat(), digest=first.raw_digest))
    db.commit()
    store_intake_batch(db, source, (edited,), (), None, LATER)
    store_intake_batch(db, source, (edited,), (), None, LATER)
    assert db.scalar(select(func.count(IntakeItem.id))) == 1
    assert db.scalar(select(func.count(IntakeRevision.id))) == 1
    revision = db.scalar(select(IntakeRevision))
    assert (revision.item_id, revision.text, revision.raw_digest) == (
        item.id, "original", first.raw_digest,
    )
    assert revision.edited_at is None
    assert revision.collected_at.replace(tzinfo=UTC) == NOW
    db.refresh(item)
    assert (item.text, item.raw_digest, item.status) == ("corrected", edited.raw_digest, "attached")
    assert item.edited_at.replace(tzinfo=UTC) == LATER
    assert item.incident_id == incident.id
    assert db.scalar(select(Evidence)).text == "original"
    assert incident.state == "triage"


@pytest.mark.parametrize("autoflush", [True, False])
def test_unchanged_delivery_deduplicates_within_and_across_batches(db, source, autoflush):
    from syosint.intake_store import store_intake_batch

    db.autoflush = autoflush
    first = store_intake_batch(db, source, (normalized(), normalized()), (), None, NOW)
    second = store_intake_batch(db, source, (normalized(),), (), None, LATER)
    assert (first.created, first.duplicates, first.quarantined) == (1, 1, 0)
    assert (second.created, second.duplicates) == (0, 1)
    assert db.scalar(select(func.count(IntakeItem.id))) == 1
    assert db.scalar(select(func.count(IntakeRevision.id))) == 0


def test_native_ids_are_scoped_to_source(db, source):
    from syosint.intake_store import store_intake_batch

    other = Source(name="Other", url="https://t.me/other_channel", language="en", kind="telegram")
    db.add(other)
    db.commit()
    store_intake_batch(db, source, (normalized(),), (), None, NOW)
    store_intake_batch(db, other, (normalized(text="other"),), (), None, NOW)
    assert db.scalar(select(func.count(IntakeItem.id))) == 2
    assert db.scalar(select(func.count(IntakeRevision.id))) == 0


def test_missing_native_id_deduplicates_by_fingerprint(db, source):
    from syosint.intake_store import store_intake_batch

    item = replace(normalized(), native_id=None)
    store_intake_batch(db, source, (item, item), (), None, NOW)
    assert db.scalar(select(func.count(IntakeItem.id))) == 1


def test_quarantine_is_platform_aware_and_idempotent(db, source):
    from syosint.intake_store import store_intake_batch
    from syosint.intake_types import QuarantinedIntakeItem

    quarantine = QuarantinedIntakeItem(platform="telegram", reason="invalid-date",
                                      raw_digest="b" * 64, native_id="43")
    first = store_intake_batch(db, source, (), (quarantine, quarantine), None, NOW)
    second = store_intake_batch(db, source, (), (quarantine,), None, LATER)
    assert (first.quarantined, second.quarantined) == (1, 0)
    row = db.scalar(select(IntakeQuarantine))
    assert (row.platform, row.reason, row.native_id) == ("telegram", "invalid-date", "43")
    assert db.scalar(select(func.count(IntakeQuarantine.id))) == 1


@pytest.mark.parametrize("failure_point", ["callback", "commit"])
def test_failure_rolls_back_items_revisions_quarantine_cursor_and_audit(db, source, failure_point):
    from syosint.intake_store import store_intake_batch
    from syosint.intake_types import QuarantinedIntakeItem

    source_id = source.id
    store_intake_batch(db, source, (normalized(),), (), None, NOW)
    db.add(TelegramCursor(source_id=source_id, last_message_id=42))
    db.commit()

    def fail(*args):
        raise RuntimeError("injected transaction failure")

    def update_cursor(session):
        cursor = session.get(TelegramCursor, source_id)
        cursor.last_message_id = 43
        record(session, "telegram.health_changed", "source", source_id,
               after={"status": "healthy"})
        session.flush()
        if failure_point == "callback":
            fail()

    if failure_point == "commit":
        event.listen(db, "before_commit", fail)
    try:
        with pytest.raises(RuntimeError, match="injected transaction failure"):
            store_intake_batch(
                db, source, (normalized(text="corrected", edited_at=LATER), normalized("43")),
                (QuarantinedIntakeItem(platform="telegram", reason="invalid-date", raw_digest="c" * 64),),
                update_cursor, LATER,
            )
    finally:
        if failure_point == "commit":
            event.remove(db, "before_commit", fail)
    assert db.scalar(select(func.count(IntakeItem.id))) == 1
    assert db.scalar(select(IntakeItem)).text == "original"
    assert db.scalar(select(func.count(IntakeRevision.id))) == 0
    assert db.scalar(select(func.count(IntakeQuarantine.id))) == 0
    assert db.scalar(select(func.count(Audit.id))) == 0
    assert db.get(TelegramCursor, source_id).last_message_id == 42
    # The same Session remains usable after rollback.
    store_intake_batch(db, source, (normalized("43"),), (), update_cursor if failure_point == "commit" else None, LATER)
    assert db.scalar(select(func.count(IntakeItem.id))) == 2


def test_failed_item_flush_does_not_advance_cursor(db, source):
    from syosint.intake_store import store_intake_batch

    source_id = source.id
    db.add(TelegramCursor(source_id=source_id, last_message_id=41))
    db.commit()

    def update_cursor(session):
        session.get(TelegramCursor, source_id).last_message_id = 42

    with pytest.raises(IntegrityError):
        store_intake_batch(db, source, (replace(normalized(), text=None),), (), update_cursor, NOW)
    assert db.get(TelegramCursor, source_id).last_message_id == 41
    assert db.scalar(select(func.count(IntakeItem.id))) == 0


def test_items_and_cursor_commit_together(db, source):
    from syosint.intake_store import store_intake_batch

    source_id = source.id

    def update_cursor(session):
        session.add(TelegramCursor(source_id=source_id, last_message_id=42))

    store_intake_batch(db, source, (normalized(),), (), update_cursor, NOW)
    with Session(db.bind) as reopened:
        assert reopened.scalar(select(IntakeItem)).platform == "telegram"
        assert reopened.get(TelegramCursor, source_id).last_message_id == 42


def test_rss_changed_digest_retains_legacy_duplicate_observation(db):
    from syosint.rss_store import store_collection
    from syosint.rss_types import NormalizedFeedItem
    from syosint.rss_collect import SourceOutcome

    source = Source(name="Feed", url="https://example.org", language="en", kind="rss")
    db.add(source)
    db.commit()
    first = NormalizedFeedItem(str(source.id), "42", "Original headline",
                               "https://example.org/42", NOW, NOW, "stable", "a" * 64)
    edited = replace(first, headline="Revised headline", raw_digest="b" * 64)
    store_collection(db, source, SourceOutcome(str(source.id), "healthy", (first,), None, None), NOW)
    summary = store_collection(db, source, SourceOutcome(str(source.id), "healthy", (edited, edited), None, None), LATER)
    assert (summary.created, summary.duplicates) == (0, 2)
    items = db.scalars(select(IntakeItem).order_by(IntakeItem.id)).all()
    assert [(item.status, item.headline, item.platform, item.native_id) for item in items] == [
        ("new", "Original headline", "rss", "42"),
        ("duplicate", "Revised headline", "rss", "42"),
    ]
    assert db.scalar(select(func.count(IntakeRevision.id))) == 0
