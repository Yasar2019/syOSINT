from datetime import UTC, datetime, timedelta
import json
from pathlib import Path

import pytest

from syosint.telegram_export import (
    PublicSchemaError, stage_telegram_wire, validate_public_telegram_wire,
    write_pending_telegram_export,
)

NOW = datetime(2026, 9, 27, 17, tzinfo=UTC)


def lead(identifier="telegram:42:7", published=None):
    return {
        "id": identifier, "status": "active",
        "channel": {"name": "Synthetic Public Channel", "username": "publicnews", "language": "mixed"},
        "url": "https://t.me/publicnews/7" if identifier.endswith(":7") else "https://t.me/publicnews/8",
        "headline": {"en": "Human-written headline", "ar": "عنوان كتبه محلل"},
        "publishedAt": (published or NOW - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "approvedAt": NOW.isoformat().replace("+00:00", "Z"),
        "revisions": [],
    }


def write(path: Path, entries):
    path.write_text(json.dumps({
        "schemaVersion": "1.0.0", "generatedAt": "2026-09-27T17:00:00Z",
        "lastEditorialUpdateAt": "2026-09-27T17:00:00Z",
        "entries": entries,
    }), encoding="utf-8")
    return path


def test_pending_sanitizes_and_staging_is_idempotent(tmp_path):
    current = write(tmp_path / "public.json", [])
    pending = write_pending_telegram_export(tmp_path / "private", [lead()], NOW)
    assert pending.parent.stat().st_mode & 0o077 == 0
    for _ in range(2):
        stage_telegram_wire(pending, current, current, NOW)
    entries = json.loads(current.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["id"] == "telegram:42:7"


def test_pending_prunes_expired_approvals_before_the_500_entry_limit(tmp_path):
    historical = []
    for index in range(1, 502):
        record = lead(published=NOW - timedelta(days=8))
        record["id"] = f"telegram:42:{index}"
        record["url"] = f"https://t.me/publicnews/{index}"
        historical.append(record)
    recent = lead()
    pending = write_pending_telegram_export(tmp_path / "private", historical + [recent], NOW)
    data = json.loads(pending.read_text())
    assert [record["id"] for record in data["entries"]] == [recent["id"]]


def test_staging_accepts_valid_correction_history_larger_than_old_2mb_cap(tmp_path):
    records = []
    for index in range(1, 41):
        record = lead(published=NOW - timedelta(days=3))
        record["id"] = f"telegram:42:{index}"
        record["url"] = f"https://t.me/publicnews/{index}"
        record["approvedAt"] = (NOW - timedelta(days=2)).isoformat().replace("+00:00", "Z")
        record["status"] = "corrected"
        record["revisions"] = [{
            "action": "corrected",
            "revisedAt": (NOW - timedelta(days=2) + timedelta(minutes=revision + 1)).isoformat().replace("+00:00", "Z"),
            "reason": {"en": "E" * 180, "ar": "ع" * 180},
            "previousHeadline": {"en": "P" * 180, "ar": "س" * 180},
        } for revision in range(100)]
        records.append(record)
    pending = write_pending_telegram_export(tmp_path / "private", records, NOW)
    assert pending.stat().st_size > 2_000_000
    current = write(tmp_path / "public.json", [])
    stage_telegram_wire(pending, current, current, NOW)
    assert len(json.loads(current.read_text())["entries"]) == 40


def test_stage_fails_closed_on_private_field_and_preserves_existing_data(tmp_path):
    original = [lead()]
    current = write(tmp_path / "public.json", original)
    pending = write(tmp_path / "pending.json", [{**lead("telegram:42:8"), "rawText": "PRIVATE SOURCE TEXT"}])
    before = current.read_bytes()
    with pytest.raises(PublicSchemaError):
        stage_telegram_wire(pending, current, current, NOW)
    assert current.read_bytes() == before
    assert b"PRIVATE SOURCE TEXT" not in current.read_bytes()


def test_history_cannot_be_rewritten_and_expired_items_are_pruned(tmp_path):
    current = write(tmp_path / "public.json", [lead(), lead("telegram:42:8", NOW - timedelta(days=8))])
    edited = lead()
    edited["headline"] = {"en": "Updated by analyst", "ar": "عدله المحلل"}
    edited["status"] = "corrected"
    edited["revisions"] = [{
        "action": "corrected", "revisedAt": "2026-09-27T18:00:00Z",
        "reason": {"en": "Attribution updated", "ar": "تحديث النسبة"},
        "previousHeadline": lead()["headline"],
    }]
    pending = write(tmp_path / "pending.json", [edited])
    stage_telegram_wire(pending, current, current, NOW)
    entries = json.loads(current.read_text())["entries"]
    assert len(entries) == 1
    assert entries[0]["status"] == "corrected"
    revised = {**edited, "revisions": [{**edited["revisions"][0],
                "previousHeadline": {"en": "Fake", "ar": "مزيف"}}]}
    write(pending, [revised])
    with pytest.raises(PublicSchemaError):
        stage_telegram_wire(pending, current, current, NOW)
    assert json.loads(current.read_text())["entries"] == entries


def test_semantic_link_validation_rejects_username_or_id_mismatch():
    for candidate in ("https://t.me/another/7", "https://t.me/publicnews/8",
                      "https://t.me/publicnews/7?token=private"):
        item = {**lead(), "url": candidate}
        with pytest.raises(PublicSchemaError):
            validate_public_telegram_wire({
                "schemaVersion": "1.0.0", "generatedAt": "2026-09-27T17:00:00Z",
                "lastEditorialUpdateAt": "2026-09-27T17:00:00Z", "entries": [item],
            })
