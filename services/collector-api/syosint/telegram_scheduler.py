"""Read-only Telegram transport and bounded local polling."""

import asyncio
import stat
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from telethon.tl.types import Channel

from .models import Source, TelegramCursor
from .telegram_media import purge_expired_media
from .telegram_client import TelethonAuthClient
from .telegram_collect import ChannelPolicyError, sync_channel
from .telegram_session import TelegramSettings, session_path
from .telegram_types import ResolvedPublicChannel, TelegramMessage


class TelethonReadTransport:
    """Expose only resolution and read operations; never join or send."""

    def __init__(self, settings: TelegramSettings):
        path = session_path(settings)
        if path.is_symlink() or not path.is_file() or path.stat().st_nlink != 1:
            raise ChannelPolicyError("login required")
        if path.parent.is_symlink() or settings.private_dir.is_symlink():
            raise ChannelPolicyError("unsafe session")
        if stat.S_IMODE(path.stat().st_mode) & 0o077:
            raise ChannelPolicyError("unsafe session")
        self._client = TelethonAuthClient(settings)
        self._entity = None

    async def is_authorized(self) -> bool:
        return await self._client.is_authorized()

    async def resolve_username(self, username: str) -> ResolvedPublicChannel:
        if not await self.is_authorized():
            raise ChannelPolicyError("login required")
        entity = await self._client._client.get_entity(username)
        if not isinstance(entity, Channel) or not entity.broadcast or not entity.username:
            raise ChannelPolicyError("public channel required")
        self._entity = entity
        return ResolvedPublicChannel(entity.id, entity.username, entity.title, True)

    async def iter_messages(self, channel_id: int, *, limit: int, since: datetime):
        if self._entity is None or self._entity.id != channel_id:
            raise ChannelPolicyError("channel not resolved")
        async for item in self._client._client.iter_messages(self._entity, limit=limit):
            if not item.date or item.date < since:
                break
            file = item.file
            yield TelegramMessage(item.id, item.raw_text or "", item.date, item.edit_date,
                                  file.mime_type if file else None, file.size if file else None)

    async def reconcile_messages(self, channel_id: int, native_ids: tuple[str, ...]) -> tuple[TelegramMessage, ...]:
        if self._entity is None or self._entity.id != channel_id:
            raise ChannelPolicyError("channel not resolved")
        if not native_ids:
            return ()
        found = await self._client._client.get_messages(self._entity, ids=[int(value) for value in native_ids])
        return tuple(TelegramMessage(
            item.id, item.raw_text or "", item.date, item.edit_date,
            item.file.mime_type if item.file else None,
            item.file.size if item.file else None,
        ) for item in found if item is not None and item.date)

    async def iter_media_chunks(self, channel_id: int, message_id: int):
        if self._entity is None or self._entity.id != channel_id:
            raise ChannelPolicyError("channel not resolved")
        message = await self._client._client.get_messages(self._entity, ids=message_id)
        if message is None or message.media is None:
            return
        async for chunk in self._client._client.iter_download(message.media, request_size=64 * 1024):
            yield chunk

    async def disconnect(self):
        await self._client.disconnect()


class TelegramScheduler:
    def __init__(self, engine: Engine, settings: TelegramSettings, *, factory=None,
                 interval_seconds: int = 300):
        self.engine = engine
        self.settings = settings
        self.factory = factory or (lambda: TelethonReadTransport(settings))
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(self.interval_seconds)

    async def poll_once(self, now: datetime | None = None) -> None:
        now = now or datetime.now(UTC)
        with Session(self.engine) as db:
            sources = tuple(db.scalars(select(Source).where(
                Source.kind == "telegram", Source.enabled.is_(True),
            )).all())
            ready = []
            for source in sources:
                cursor = db.get(TelegramCursor, source.id)
                if cursor and ((cursor.rate_limit_until and cursor.rate_limit_until.replace(tzinfo=UTC) > now)
                               or (cursor.next_poll_at and cursor.next_poll_at.replace(tzinfo=UTC) > now)):
                    continue
                ready.append(source.id)
        for source_id in ready:
            transport = None
            try:
                transport = self.factory()
                await sync_channel(self.engine, source_id, transport, now,
                                   media_root=self.settings.private_dir / "telegram" / "media")
            except Exception as error:
                # No exception text or identifiers are logged. One source cannot stop another.
                delay = getattr(error, "seconds", None)
                if not isinstance(delay, int) or not 0 < delay <= 86400:
                    delay = 300
                    category = "collection-failed"
                else:
                    category = "rate-limited"
                with Session(self.engine) as db:
                    cursor = db.get(TelegramCursor, source_id)
                    if cursor is None:
                        cursor = TelegramCursor(source_id=source_id)
                        db.add(cursor)
                    cursor.last_attempt_at = now
                    cursor.last_status = "delayed"
                    cursor.last_error_category = category
                    cursor.consecutive_failures = (cursor.consecutive_failures or 0) + 1
                    cursor.rate_limit_until = now + timedelta(seconds=delay) if category == "rate-limited" else None
                    cursor.next_poll_at = now + timedelta(seconds=delay)
                    db.commit()
            finally:
                if transport is not None:
                    try:
                        await transport.disconnect()
                    except Exception:
                        pass
        try:
            with Session(self.engine) as db:
                purge_expired_media(db, now, self.settings.private_dir / "telegram" / "media")
        except Exception:
            # Path violations and filesystem failures never delete an unverified file.
            pass
