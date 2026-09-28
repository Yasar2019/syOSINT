"""Bounded, read-only local Telegram intake. Never projects public records."""

import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .intake_store import store_intake_batch
from .intake_types import NormalizedIntakeItem, QuarantinedIntakeItem
from .models import IntakeItem, MediaAsset, Source, TelegramCursor
from .telegram_media import ALLOWED_MIME_TYPES, MediaMetadata, MediaPolicy, preserve_media_async
from .telegram_session import TelegramSettings
from .telegram_types import ResolvedPublicChannel, SyncSummary, TelegramMessage


USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
BACKFILL_LIMIT = 500
BACKFILL_DAYS = 7
RECONCILE_LIMIT = 100
MAX_POST_LENGTH = 20_000


class ChannelPolicyError(ValueError):
    pass


class TelegramTransport(Protocol):
    async def resolve_username(self, username: str) -> ResolvedPublicChannel: ...
    def iter_messages(self, channel_id: int, *, limit: int, since: datetime) -> AsyncIterator[TelegramMessage]: ...
    async def reconcile_messages(self, channel_id: int, native_ids: tuple[str, ...]) -> tuple[TelegramMessage, ...]: ...
    def iter_media_chunks(self, channel_id: int, message_id: int) -> AsyncIterator[bytes]: ...


async def resolve_public_channel(username: str, transport: TelegramTransport) -> ResolvedPublicChannel:
    if not USERNAME.fullmatch(username) or username.lower().startswith("joinchat"):
        raise ChannelPolicyError("public username required")
    entity = await transport.resolve_username(username)
    if not entity.public or not entity.username or entity.channel_id <= 0:
        raise ChannelPolicyError("public channel required")
    if entity.username.casefold() != username.casefold():
        raise ChannelPolicyError("username mismatch")
    return entity


def _normalized(source: Source, post: TelegramMessage, now: datetime) -> NormalizedIntakeItem:
    username = source.public_identifier or ""
    if not USERNAME.fullmatch(username) or post.message_id <= 0:
        raise ValueError("invalid public post identity")
    if (post.published_at.tzinfo is None or post.published_at > now + timedelta(hours=24)
            or post.edited_at is not None and post.edited_at.tzinfo is None):
        raise ValueError("invalid public post date")
    if not isinstance(post.text, str) or not post.text.strip() or len(post.text) > MAX_POST_LENGTH:
        raise ValueError("invalid public post text")
    native_id = str(post.message_id)
    url = f"https://t.me/{username}/{native_id}"
    return NormalizedIntakeItem(
        platform="telegram", native_id=native_id, headline=None, url=url,
        text=post.text, published_at=post.published_at.astimezone(UTC),
        edited_at=post.edited_at.astimezone(UTC) if post.edited_at else None,
        collected_at=now, fingerprint=sha256(f"{source.id}\0{native_id}".encode()).hexdigest(),
        # A source edit can leave its caption unchanged while updating media or
        # the edit timestamp. Any such change invalidates an earlier review.
        raw_digest=sha256(json.dumps({
            "text": post.text,
            "edited_at": post.edited_at.astimezone(UTC).isoformat() if post.edited_at else None,
            "media_mime_type": post.media_mime_type,
            "media_size": post.media_size,
        }, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
    )


async def sync_channel(engine: Engine, source_id: int, transport: TelegramTransport,
                       now: datetime, *, media_root: Path | None = None) -> SyncSummary:
    """Network work precedes one atomic item/cursor transaction."""
    with Session(engine) as db:
        source = db.get(Source, source_id)
        if source is None or source.kind != "telegram" or not source.enabled:
            raise ChannelPolicyError("approved enabled channel required")
        username = source.public_identifier or ""
        cursor = db.get(TelegramCursor, source_id)
        if cursor is None or cursor.channel_id is None:
            raise ChannelPolicyError("channel identity not approved")
        approved_channel_id = cursor.channel_id
        prior_id = cursor.last_message_id if cursor else None
        previous = db.scalars(select(IntakeItem).where(
            IntakeItem.source_id == source_id, IntakeItem.platform == "telegram",
            IntakeItem.deleted_at.is_(None),
        ).order_by(IntakeItem.id.desc()).limit(RECONCILE_LIMIT)).all()
        previous_ids = tuple(item.native_id for item in previous if item.native_id)
        # All DB sessions are closed before awaiting network I/O.
        source_snapshot = Source(id=source.id, public_identifier=username,
                                 media_enabled=source.media_enabled)

    entity = await resolve_public_channel(username, transport)
    if entity.channel_id != approved_channel_id:
        raise ChannelPolicyError("channel identity changed")
    since = now - timedelta(days=BACKFILL_DAYS)
    items = []
    quarantined = []
    media_candidates: dict[str, TelegramMessage] = {}
    max_id = prior_id or 0
    async for post in transport.iter_messages(entity.channel_id, limit=BACKFILL_LIMIT, since=since):
        if post.published_at.tzinfo is None or post.published_at < since:
            continue
        try:
            items.append(_normalized(source_snapshot, post, now))
            if post.media_mime_type:
                media_candidates[str(post.message_id)] = post
            max_id = max(max_id, post.message_id)
        except ValueError:
            quarantined.append(QuarantinedIntakeItem(
                platform="telegram", reason="invalid-post",
                raw_digest=sha256(repr((post.message_id, post.text)).encode()).hexdigest(),
                native_id=str(post.message_id),
            ))
    if previous_ids:
        observed = await transport.reconcile_messages(entity.channel_id, previous_ids)
        observed_ids = {str(post.message_id) for post in observed}
        missing = set(previous_ids) - observed_ids
        batch_ids = {item.native_id for item in items}
        for post in observed:
            if str(post.message_id) not in batch_ids:
                try:
                    items.append(_normalized(source_snapshot, post, now))
                    if post.media_mime_type:
                        media_candidates[str(post.message_id)] = post
                except ValueError:
                    quarantined.append(QuarantinedIntakeItem(
                        platform="telegram", reason="invalid-post",
                        raw_digest=sha256(repr((post.message_id, post.text)).encode()).hexdigest(),
                        native_id=str(post.message_id),
                    ))
    else:
        missing = set()

    with Session(engine) as db:
        source = db.get(Source, source_id)
        if source is None or source.kind != "telegram" or not source.enabled or source.public_identifier != username:
            raise ChannelPolicyError("channel approval changed")
        current = db.get(TelegramCursor, source_id)
        if current is None or current.channel_id != approved_channel_id:
            raise ChannelPolicyError("channel identity changed")

        def update_cursor(session: Session) -> None:
            cursor = session.get(TelegramCursor, source_id)
            if cursor is None:
                cursor = TelegramCursor(source_id=source_id)
                session.add(cursor)
            cursor.last_message_id = max(cursor.last_message_id or 0, max_id) or None
            cursor.last_attempt_at = now
            cursor.last_success_at = now
            cursor.next_poll_at = now + timedelta(minutes=5)
            cursor.consecutive_failures = 0
            cursor.last_status = "healthy"
            cursor.last_error_category = None
            if missing:
                for item in session.scalars(select(IntakeItem).where(
                    IntakeItem.source_id == source_id, IntakeItem.native_id.in_(missing),
                    IntakeItem.platform == "telegram", IntakeItem.deleted_at.is_(None),
                )):
                    item.deleted_at = now

        summary = store_intake_batch(db, source, items, quarantined, update_cursor, now)
    if source_snapshot.media_enabled and media_candidates:
        root = media_root or TelegramSettings.load().private_dir / "telegram" / "media"
        for native_id, post in media_candidates.items():
            if post.media_mime_type not in ALLOWED_MIME_TYPES or (
                post.media_size is not None and (post.media_size <= 0 or post.media_size > 10_000_000)
            ):
                continue
            with Session(engine) as db:
                current_source = db.get(Source, source_id)
                if current_source is None or not current_source.media_enabled:
                    break
                saved = db.scalar(select(IntakeItem).where(
                    IntakeItem.source_id == source_id, IntakeItem.platform == "telegram",
                    IntakeItem.native_id == native_id,
                ))
                has_asset = saved is None or db.scalar(select(MediaAsset.id).where(
                    MediaAsset.item_id == saved.id, MediaAsset.deleted_at.is_(None),
                ).limit(1)) is not None
                item_id = saved.id if saved else None
            if has_asset or item_id is None:
                continue
            asset = None
            try:
                asset = await preserve_media_async(
                    transport.iter_media_chunks(entity.channel_id, post.message_id),
                    MediaMetadata(item_id, post.media_mime_type, now),
                    MediaPolicy(enabled=True), root,
                )
                if asset is not None:
                    with Session(engine) as db:
                        current_source = db.get(Source, source_id)
                        if current_source is None or not current_source.media_enabled:
                            Path(asset.local_path).unlink(missing_ok=True)
                            continue
                        db.add(asset)
                        db.commit()
            except Exception:
                if asset is not None:
                    Path(asset.local_path).unlink(missing_ok=True)
                # Item collection remains durable; optional media cannot block it.
                pass
    oldest = min((item.published_at for item in items), default=None)
    return SyncSummary(summary.created, summary.duplicates, summary.quarantined, oldest)
