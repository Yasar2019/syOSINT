import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
import inspect

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import FeedCursor, Source
from .rss_collect import SourceOutcome, collect_sources
from .rss_store import store_collection
from .rss_types import FeedSource
from .safe_http import HttpValidators, SafeFeedClient


Collector = Callable[
    [Source, datetime, HttpValidators | None],
    SourceOutcome | Awaitable[SourceOutcome],
]


@dataclass(frozen=True)
class SchedulerSummary:
    attempted: int
    not_due: int
    overlap_skipped: bool = False


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def collect_due_sources(
    engine: Engine, collector: Collector, now: datetime
) -> SchedulerSummary:
    with Session(engine) as db:
        sources = tuple(
            db.scalars(
                select(Source).where(Source.kind == "rss", Source.enabled.is_(True))
            )
        )
        due = []
        for source in sources:
            cursor = db.get(FeedCursor, source.id)
            if (
                cursor is None
                or cursor.next_poll_at is None
                or _utc(cursor.next_poll_at) <= _utc(now)
            ):
                validators = (
                    HttpValidators(cursor.etag, cursor.last_modified)
                    if cursor is not None
                    else None
                )
                due.append((source.id, validators))

    for source_id, validators in due:
        with Session(engine) as db:
            source = db.get(Source, source_id)
            if inspect.iscoroutinefunction(collector):
                outcome = await collector(source, now, validators)
            else:
                collected = await asyncio.to_thread(
                    collector, source, now, validators
                )
                outcome = await collected if inspect.isawaitable(collected) else collected
            store_collection(db, source, outcome, now)
    return SchedulerSummary(len(due), len(sources) - len(due))


def _collect_source(
    source: Source,
    now: datetime,
    validators: HttpValidators | None,
    client: SafeFeedClient,
) -> SourceOutcome:
    required_terms = (
        ("سوريا", "سوري", "سورية")
        if source.language == "ar"
        else ("Syria", "Syrian")
    )
    feed_source = FeedSource(
        id=str(source.id),
        label={"en": source.name, "ar": source.name},
        feed_url=source.feed_url or source.url,
        homepage_url=source.url,
        language=source.language,
        enabled=source.enabled,
        required_terms=required_terms,
    )
    return collect_sources(
        (feed_source,),
        None,
        now,
        client,
        validators={feed_source.id: validators} if validators else None,
    ).outcomes[0]


def default_collector(
    source: Source,
    now: datetime,
    validators: HttpValidators | None = None,
) -> SourceOutcome:
    return _collect_source(source, now, validators, SafeFeedClient())


class ScheduledCollector:
    def __init__(self) -> None:
        self._client = SafeFeedClient()

    def __call__(
        self,
        source: Source,
        now: datetime,
        validators: HttpValidators | None = None,
    ) -> SourceOutcome:
        return _collect_source(source, now, validators, self._client)

    def cancel(self) -> None:
        self._client.close()


class RssScheduler:
    def __init__(
        self,
        engine: Engine,
        collector: Collector | None = None,
        *,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        tick_seconds: float = 5.0,
    ) -> None:
        self._engine = engine
        self._collector = collector or ScheduledCollector()
        self._now = now
        self._tick_seconds = tick_seconds
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._task: asyncio.Task | None = None

    async def run_once(self) -> SchedulerSummary:
        if self._lock.locked():
            return SchedulerSummary(0, 0, overlap_skipped=True)
        async with self._lock:
            return await collect_due_sources(
                self._engine, self._collector, self._now()
            )

    async def _run(self) -> None:
        while not self._stop.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self._tick_seconds
                )
            except TimeoutError:
                pass

    def start(self) -> asyncio.Task:
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(), name="syosint-rss-scheduler")
        return self._task

    async def stop(self) -> None:
        self._stop.set()
        cancel_collector = getattr(self._collector, "cancel", None)
        if cancel_collector is not None:
            cancel_collector()
        elif self._task is not None and not self._task.done():
            self._task.cancel()
        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
