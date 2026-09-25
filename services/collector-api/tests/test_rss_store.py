from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from syosint.db import database
from syosint.models import Audit, FeedCursor, FeedItem, FeedQuarantine, Source
from syosint.rss_collect import SourceOutcome
from syosint.rss_store import store_collection
from syosint.rss_types import NormalizedFeedItem, QuarantinedItem
from syosint.safe_http import HttpValidators


NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
ITEM = NormalizedFeedItem(
    source_id="feed-1",
    native_id="native-1",
    headline="Syria update",
    url="https://example.org/report",
    published_at=NOW,
    collected_at=NOW,
    fingerprint="fingerprint-1",
    raw_digest="a" * 64,
)


def add_source(engine):
    with Session(engine) as db:
        source = Source(
            name="Example feed",
            url="https://example.org/",
            language="en",
            kind="rss",
            feed_url="https://example.org/rss.xml",
        )
        db.add(source)
        db.commit()
        db.refresh(source)
        return source.id


def outcome(status="healthy", items=(ITEM,), quarantined=()):
    return SourceOutcome(
        source_id="feed-1",
        status=status,
        items=items,
        error_category=None if status != "delayed" else "timeout",
        validators=HttpValidators(etag='"v1"', last_modified="last-modified"),
        quarantined=quarantined,
    )


def test_migration_upgrades_initial_schema_and_survives_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'vault.sqlite'}"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "0001")
    from sqlalchemy import create_engine, text

    initial = create_engine(url)
    with initial.begin() as connection:
        connection.execute(
            text(
                "insert into sources (name, url, language) "
                "values ('Existing source', 'https://existing.example', 'en')"
            )
        )
    initial.dispose()

    first = database(url)
    assert {
        "intake_items",
        "feed_cursors",
        "intake_quarantine",
    }.issubset(inspect(first).get_table_names())
    assert {"kind", "feed_url", "enabled", "poll_interval_minutes"}.issubset(
        {column["name"] for column in inspect(first).get_columns("sources")}
    )
    with Session(first) as db:
        assert db.scalar(select(Source)).name == "Existing source"
    first.dispose()

    second = database(url)
    assert inspect(second).get_unique_constraints("intake_items")[0][
        "column_names"
    ] == ["source_id", "fingerprint"]


def test_collection_is_idempotent_and_persists_cursor(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
    source_id = add_source(engine)

    with Session(engine) as db:
        source = db.get(Source, source_id)
        first = store_collection(db, source, outcome(), NOW)
    with Session(engine) as db:
        source = db.get(Source, source_id)
        second = store_collection(db, source, outcome(), NOW)

    assert first.created == 1
    assert second.created == 0
    assert second.duplicates == 1
    with Session(engine) as db:
        cursor = db.get(FeedCursor, source_id)
        assert cursor.etag == '"v1"'
        assert cursor.consecutive_failures == 0
        assert {item.status for item in db.scalars(select(FeedItem)).all()} == {
            "new",
            "duplicate",
        }


def test_delayed_health_and_quarantine_are_transactional_and_deduplicated(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
    source_id = add_source(engine)
    quarantined = QuarantinedItem(
        source_id="feed-1",
        reason="future-published-at",
        raw_digest="b" * 64,
        native_id="future-1",
        headline="Future Syria report",
    )

    with Session(engine) as db:
        source = db.get(Source, source_id)
        store_collection(
            db,
            source,
            outcome("delayed", items=(), quarantined=(quarantined,)),
            NOW,
        )
    with Session(engine) as db:
        source = db.get(Source, source_id)
        store_collection(
            db,
            source,
            outcome("delayed", items=(), quarantined=(quarantined,)),
            NOW,
        )

    with Session(engine) as db:
        cursor = db.get(FeedCursor, source_id)
        assert cursor.consecutive_failures == 2
        assert cursor.last_error_category == "timeout"
        assert len(db.scalars(select(FeedQuarantine)).all()) == 1
        assert [row.action for row in db.scalars(select(Audit)).all()] == [
            "feed.health_changed"
        ]


def test_not_modified_updates_schedule_without_audit_noise(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
    source_id = add_source(engine)
    with Session(engine) as db:
        source = db.get(Source, source_id)
        store_collection(db, source, outcome("not-modified", items=()), NOW)

    with Session(engine) as db:
        assert db.scalars(select(Audit)).all() == []
        cursor = db.get(FeedCursor, source_id)
        assert cursor.next_poll_at.replace(tzinfo=UTC) > NOW
