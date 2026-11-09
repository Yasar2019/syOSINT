"""Optional inert local media storage. Never reads media with AI or exports it."""

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import AsyncIterable, Iterable
from uuid import uuid4

from sqlalchemy.orm import Session

from .models import MediaAsset


ALLOWED_MIME_TYPES = frozenset({
    "image/jpeg", "image/png", "image/webp", "video/mp4", "application/pdf",
})


class MediaPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class MediaPolicy:
    enabled: bool
    max_bytes: int = 10_000_000
    retention_days: int = 30


@dataclass(frozen=True)
class MediaMetadata:
    item_id: int
    mime_type: str
    collected_at: datetime


def _media_root(destination: Path) -> Path:
    root = Path(destination)
    if root.is_symlink() or root.parent.is_symlink():
        raise MediaPolicyError("unsafe path")
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise MediaPolicyError("unsafe path")
    root.chmod(0o700)
    return root.resolve()


def preserve_media(stream: Iterable[bytes], metadata: MediaMetadata,
                   policy: MediaPolicy, destination: Path) -> MediaAsset | None:
    if not policy.enabled:
        return None
    if (policy.max_bytes <= 0 or policy.max_bytes > 10_000_000 or
            policy.retention_days <= 0 or policy.retention_days > 30):
        raise MediaPolicyError("invalid media policy")
    if metadata.mime_type not in ALLOWED_MIME_TYPES:
        raise MediaPolicyError("unsupported MIME")
    if metadata.item_id <= 0 or metadata.collected_at.tzinfo is None:
        raise MediaPolicyError("invalid media metadata")
    root = _media_root(destination)
    fd, pending = tempfile.mkstemp(prefix=".pending-", dir=root)
    size = 0
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as output:
            os.chmod(pending, 0o600)
            for chunk in stream:
                if not isinstance(chunk, bytes):
                    raise MediaPolicyError("invalid media chunk")
                size += len(chunk)
                if size > policy.max_bytes:
                    raise MediaPolicyError("size limit exceeded")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if size == 0:
            raise MediaPolicyError("empty media")
        final = root / f"{uuid4().hex}.bin"
        os.replace(pending, final)
        return MediaAsset(
            item_id=metadata.item_id, local_path=str(final),
            mime_type=metadata.mime_type, byte_size=size, sha256=digest.hexdigest(),
            collected_at=metadata.collected_at,
            expires_at=metadata.collected_at + timedelta(days=policy.retention_days),
        )
    finally:
        Path(pending).unlink(missing_ok=True)


async def preserve_media_async(stream: AsyncIterable[bytes], metadata: MediaMetadata,
                               policy: MediaPolicy, destination: Path) -> MediaAsset | None:
    """Bound an asynchronous download while writing directly to a private file."""
    if not policy.enabled:
        return None
    if (policy.max_bytes <= 0 or policy.max_bytes > 10_000_000 or
            policy.retention_days <= 0 or policy.retention_days > 30):
        raise MediaPolicyError("invalid media policy")
    if metadata.mime_type not in ALLOWED_MIME_TYPES:
        raise MediaPolicyError("unsupported MIME")
    if metadata.item_id <= 0 or metadata.collected_at.tzinfo is None:
        raise MediaPolicyError("invalid media metadata")
    root = _media_root(destination)
    fd, pending = tempfile.mkstemp(prefix=".pending-", dir=root)
    size = 0
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as output:
            os.chmod(pending, 0o600)
            async for chunk in stream:
                if not isinstance(chunk, bytes):
                    raise MediaPolicyError("invalid media chunk")
                size += len(chunk)
                if size > policy.max_bytes:
                    raise MediaPolicyError("size limit exceeded")
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if size == 0:
            raise MediaPolicyError("empty media")
        final = root / f"{uuid4().hex}.bin"
        os.replace(pending, final)
        return MediaAsset(
            item_id=metadata.item_id, local_path=str(final),
            mime_type=metadata.mime_type, byte_size=size, sha256=digest.hexdigest(),
            collected_at=metadata.collected_at,
            expires_at=metadata.collected_at + timedelta(days=policy.retention_days),
        )
    finally:
        Path(pending).unlink(missing_ok=True)


def purge_expired_media(db: Session, now: datetime, media_root: Path) -> int:
    """Compatibility entrypoint; apply all hold/link and descriptor protections."""
    from .retention import run_retention
    # An existing caller transaction must not race an independently locked cleanup.
    if db.new or db.dirty or db.deleted:
        raise MediaPolicyError("pending changes")
    db.rollback()
    result = run_retention(db.get_bind(), media_root, now, apply=True, media_only=True)
    db.expire_all()
    if result["failed"]:
        raise MediaPolicyError("unsafe path or media failure")
    return result["media"]
