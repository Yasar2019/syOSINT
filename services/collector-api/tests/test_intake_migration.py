from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from syosint import models


NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def migration_config(engine):
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", str(engine.url))
    return config


def database_at_revision(tmp_path, revision):
    engine = create_engine(f"sqlite:///{tmp_path / 'migration.sqlite'}")
    command.upgrade(migration_config(engine), revision)
    return engine


def seed_rss_records(engine):
    # Reflect the real 0002 schema: current ORM models must not create the fixture.
    metadata = MetaData()
    metadata.reflect(engine)
    tables = metadata.tables
    with engine.begin() as connection:
        connection.execute(tables["sources"].insert(), [
            dict(id=11, name="RSS source", url="https://example.org", language="en", kind="rss"),
            dict(id=12, name="Manual source", url="https://manual.example.org", language="ar", kind="manual"),
        ])
        connection.execute(tables["incidents"].insert(), dict(
            id=29, fields={"title": "Reviewed incident"}, state="triage", review={},
            created_at=NOW, updated_at=NOW,
        ))
        connection.execute(tables["feed_items"].insert(), [
            dict(id=item_id, source_id=11, fingerprint=f"fingerprint-{item_id}",
                 native_id=native_id, headline=f"Headline {item_id}",
                 url=f"https://example.org/{item_id}", text=f"Private text {item_id}",
                 published_at=NOW, collected_at=NOW, raw_digest=str(item_id) * 32,
                 status=status, incident_id=incident_id)
            for item_id, native_id, status, incident_id in [
                (41, "native-41", "promoted", 29),
                (42, "native-42", "attached", 29),
                (43, "native-41", "duplicate", None),
                (44, None, "new", None),
                (45, None, "new", None),
            ]
        ])
        connection.execute(tables["feed_cursors"].insert(), dict(
            source_id=11, etag='"rss-v1"', last_modified="yesterday",
            last_attempt_at=NOW, last_success_at=NOW, next_poll_at=NOW,
            consecutive_failures=2, last_status="delayed", last_error_category="timeout",
        ))
        connection.execute(tables["feed_quarantine"].insert(), dict(
            id=57, source_id=11, reason="future-published-at", raw_digest="f" * 64,
            native_id="future", headline="Future report", created_at=NOW,
        ))
    with engine.connect() as connection:
        return {
            name: connection.execute(select(tables[name])).mappings().all()
            for name in ("feed_items", "feed_cursors", "feed_quarantine", "incidents")
        }


def test_0003_preserves_rss_identity_statuses_incident_links_and_quarantine(tmp_path):
    engine = database_at_revision(tmp_path, "0002")
    before = seed_rss_records(engine)
    assert hasattr(models, "IntakeItem"), "Shared intake model does not exist yet"

    command.upgrade(migration_config(engine), "0003")
    inspector = inspect(engine)
    assert {"intake_items", "intake_revisions", "intake_quarantine", "telegram_cursors", "media_assets", "feed_cursors"} <= set(inspector.get_table_names())
    assert not {"feed_items", "feed_quarantine"} & set(inspector.get_table_names())
    assert {"public_identifier", "review_notes", "media_enabled"} <= {
        column["name"] for column in inspector.get_columns("sources")
    }
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        for old_name, new_name in (
            ("feed_items", "intake_items"),
            ("feed_cursors", "feed_cursors"),
            ("feed_quarantine", "intake_quarantine"),
            ("incidents", "incidents"),
        ):
            old_columns = list(before[old_name][0])
            current = connection.execute(select(*[
                metadata.tables[new_name].c[name] for name in old_columns
            ])).mappings().all()
            assert current == before[old_name]
    with Session(engine) as db:
        item = db.get(models.IntakeItem, 41)
        assert (item.platform, item.status, item.incident_id) == ("rss", "promoted", 29)
        assert item.edited_at is None and item.deleted_at is None
        for source in db.scalars(select(models.Source)):
            assert source.public_identifier is None
            assert source.review_notes is None
            assert source.media_enabled is False
        assert db.get(models.IntakeQuarantine, 57).platform == "rss"
    command.upgrade(migration_config(engine), "head")
    with engine.connect() as connection:
        assert connection.scalar(text("select count(*) from intake_items")) == 5


def test_shared_identity_constraints_allow_legacy_duplicates_and_null_native_ids(tmp_path):
    engine = database_at_revision(tmp_path, "0002")
    seed_rss_records(engine)
    assert hasattr(models, "IntakeItem"), "Shared intake model does not exist yet"
    command.upgrade(migration_config(engine), "0003")
    table = models.IntakeItem.__table__
    with engine.connect() as connection:
        original = dict(connection.execute(select(table).where(table.c.id == 41)).mappings().one())
    original.pop("id")
    with engine.begin() as connection:
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(table.insert(), dict(original, fingerprint="different"))
        with pytest.raises(IntegrityError):
            with connection.begin_nested():
                connection.execute(table.insert(), dict(original, native_id="different"))
        connection.execute(table.insert(), dict(original, fingerprint="duplicate-two", status="duplicate"))
        connection.execute(table.insert(), dict(original, fingerprint="without-native", native_id=None))
        connection.execute(table.insert(), dict(original, source_id=12))


def test_shared_companion_records_survive_restart(tmp_path):
    engine = database_at_revision(tmp_path, "0002")
    seed_rss_records(engine)
    assert hasattr(models, "IntakeRevision"), "Shared companion models do not exist yet"
    command.upgrade(migration_config(engine), "0003")
    with Session(engine) as db:
        db.add(models.IntakeRevision(item_id=41, text="Original private text", raw_digest="a" * 64, edited_at=NOW, collected_at=NOW))
        db.add(models.TelegramCursor(source_id=12, last_message_id=123, reconcile_from_id=100, rate_limit_until=NOW))
        db.add(models.MediaAsset(item_id=41, local_path="private-data/media/hash.bin", mime_type="image/jpeg", byte_size=42, sha256="b" * 64, collected_at=NOW, expires_at=NOW))
        db.commit()
    engine.dispose()
    with Session(engine) as db:
        assert db.scalar(select(models.IntakeRevision)).text == "Original private text"
        cursor = db.get(models.TelegramCursor, 12)
        assert (cursor.last_message_id, cursor.reconcile_from_id, cursor.consecutive_failures) == (123, 100, 0)
        asset = db.scalar(select(models.MediaAsset))
        assert (asset.byte_size, asset.mime_type, asset.deleted_at) == (42, "image/jpeg", None)


def test_rss_only_downgrade_preserves_legacy_records(tmp_path):
    engine = database_at_revision(tmp_path, "0002")
    before = seed_rss_records(engine)
    command.upgrade(migration_config(engine), "0003")
    command.downgrade(migration_config(engine), "0002")
    metadata = MetaData()
    metadata.reflect(engine)
    with engine.connect() as connection:
        for table, rows in before.items():
            assert connection.execute(select(metadata.tables[table])).mappings().all() == rows
    assert "intake_items" not in inspect(engine).get_table_names()


@pytest.mark.parametrize("shared_data", [
    "UPDATE sources SET kind='telegram' WHERE id=12",
    "UPDATE sources SET public_identifier='public_channel' WHERE id=12",
    "UPDATE sources SET review_notes='Approved' WHERE id=12",
    "UPDATE sources SET media_enabled=1 WHERE id=12",
    "UPDATE intake_items SET platform='telegram' WHERE id=41",
    "UPDATE intake_items SET edited_at='2026-09-24' WHERE id=41",
    "UPDATE intake_items SET deleted_at='2026-09-24' WHERE id=41",
    "UPDATE intake_items SET headline=NULL WHERE id=41",
    "UPDATE intake_quarantine SET platform='telegram' WHERE id=57",
    "INSERT INTO telegram_cursors (source_id) VALUES (12)",
    "INSERT INTO intake_revisions (item_id,text,raw_digest,collected_at) VALUES (41,'revision','digest','2026-09-24')",
    "INSERT INTO media_assets (item_id,local_path,mime_type,byte_size,sha256,collected_at,expires_at) VALUES (41,'private-data/media/file','image/jpeg',1,'digest','2026-09-24','2026-10-24')",
])
def test_downgrade_refuses_shared_data_before_mutating_schema(tmp_path, shared_data):
    engine = database_at_revision(tmp_path, "0002")
    seed_rss_records(engine)
    command.upgrade(migration_config(engine), "0003")
    with engine.begin() as connection:
        connection.execute(text(shared_data))
    before = set(inspect(engine).get_table_names())
    with pytest.raises(RuntimeError, match="shared intake data"):
        command.downgrade(migration_config(engine), "0002")
    assert set(inspect(engine).get_table_names()) == before
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0003"
        assert connection.scalar(text("SELECT count(*) FROM intake_items")) == 5
