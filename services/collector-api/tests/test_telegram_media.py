from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syosint.db import database
from syosint.models import Audit, IntakeItem, MediaAsset, Source
from syosint.telegram_media import (
    MediaMetadata, MediaPolicy, MediaPolicyError, preserve_media, purge_expired_media,
    preserve_media_async,
)


NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


def meta(mime_type="image/png", item_id=1):
    return MediaMetadata(item_id=item_id, mime_type=mime_type, collected_at=NOW)


def chunks(total):
    for _ in range(total // 4096):
        yield b"x" * 4096
    if total % 4096:
        yield b"x" * (total % 4096)


def test_disabled_policy_never_consumes_stream(tmp_path):
    def forbidden():
        raise AssertionError("disabled media must not download")
        yield b""

    assert preserve_media(forbidden(), meta(), MediaPolicy(enabled=False), tmp_path) is None
    assert list(tmp_path.iterdir()) == []


def test_oversized_media_leaves_no_durable_or_temporary_files(tmp_path):
    with pytest.raises(MediaPolicyError, match="size limit"):
        preserve_media(chunks(10_000_001), meta(), MediaPolicy(enabled=True), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_executable_mime_rejected_before_stream_consumed(tmp_path):
    with pytest.raises(MediaPolicyError, match="MIME"):
        preserve_media(chunks(10), meta("application/x-msdownload"), MediaPolicy(enabled=True), tmp_path)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_async_download_enforces_size_and_removes_partial_file(tmp_path):
    async def stream():
        yield b"x" * 9_000_000
        yield b"x" * 1_000_001

    with pytest.raises(MediaPolicyError, match="size limit"):
        await preserve_media_async(stream(), meta(), MediaPolicy(enabled=True), tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_successful_media_has_digest_and_30_day_expiry(tmp_path):
    asset = preserve_media(chunks(80), meta(), MediaPolicy(enabled=True), tmp_path)
    assert asset.byte_size == 80
    assert asset.mime_type == "image/png"
    assert asset.expires_at == NOW + timedelta(days=30)
    assert Path(asset.local_path).read_bytes() == b"x" * 80
    assert Path(asset.local_path).parent == tmp_path


def test_symlinked_destination_cannot_redirect_media_outside_private_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    target = tmp_path / "private-media"
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(MediaPolicyError, match="unsafe path"):
        preserve_media(chunks(10), meta(), MediaPolicy(enabled=True), target)
    assert list(outside.iterdir()) == []


def test_expired_media_deleted_and_audited(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'private.sqlite'}")
    root = tmp_path / "media"
    root.mkdir()
    owned = root / "owned.bin"
    owned.write_bytes(b"synthetic")
    with Session(engine) as db:
        source = Source(name="Public", url="https://t.me/publicnews", kind="telegram", language="en")
        db.add(source)
        db.flush()
        item = IntakeItem(source_id=source.id, platform="telegram", fingerprint="fingerprint",
                          native_id="1", headline=None, url="https://t.me/publicnews/1",
                          text="synthetic", published_at=NOW, collected_at=NOW,
                          raw_digest="a" * 64, status="new")
        db.add(item)
        db.flush()
        asset = MediaAsset(item_id=item.id, local_path=str(owned), mime_type="image/png",
                           byte_size=9, sha256="b" * 64, collected_at=NOW,
                           expires_at=NOW - timedelta(seconds=1))
        db.add(asset)
        db.commit()
        assert purge_expired_media(db, NOW, root) == 1
        assert purge_expired_media(db, NOW, root) == 0
        assert not owned.exists()
        assert db.scalar(select(MediaAsset)).deleted_at is not None
        assert [audit.action for audit in db.scalars(select(Audit))] == ["media.deleted"]


def test_purge_rejects_asset_path_outside_media_root(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'private.sqlite'}")
    root = tmp_path / "media"
    root.mkdir()
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"preserve")
    with Session(engine) as db:
        source = Source(name="Public", url="https://t.me/publicnews", kind="telegram", language="en")
        db.add(source)
        db.flush()
        item = IntakeItem(source_id=source.id, platform="telegram", fingerprint="fingerprint",
                          native_id="1", headline=None, url="https://t.me/publicnews/1",
                          text="synthetic", published_at=NOW, collected_at=NOW,
                          raw_digest="a" * 64, status="new")
        db.add(item)
        db.flush()
        db.add(MediaAsset(item_id=item.id, local_path=str(outside), mime_type="image/png",
                          byte_size=8, sha256="b" * 64, collected_at=NOW,
                          expires_at=NOW - timedelta(seconds=1)))
        db.commit()
        with pytest.raises(MediaPolicyError, match="unsafe path"):
            purge_expired_media(db, NOW, root)
        assert outside.read_bytes() == b"preserve"
