import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
import threading

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from syosint.api import create_app
from syosint.db import database
from syosint.models import FeedCursor, Source
from syosint.rss_collect import SourceOutcome
from syosint.rss_scheduler import RssScheduler, collect_due_sources


NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)


def add_source(engine, name, next_poll_at=None):
    with Session(engine) as db:
        source = Source(
            name=name,
            url=f"https://{name}.example/",
            language="en",
            kind="rss",
            feed_url=f"https://{name}.example/rss",
        )
        db.add(source)
        db.flush()
        if next_poll_at is not None:
            db.add(FeedCursor(source_id=source.id, next_poll_at=next_poll_at))
        db.commit()
        return source.id


def healthy(source):
    return SourceOutcome(str(source.id), "healthy", (), None, None)


def test_collects_only_due_sources_and_persists_thirty_minute_schedule(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
    due_id = add_source(engine, "due")
    future_id = add_source(engine, "future", NOW + timedelta(minutes=1))
    called = []

    async def collector(source, now, validators):
        called.append((source.id, now))
        return healthy(source)

    summary = asyncio.run(collect_due_sources(engine, collector, NOW))

    assert summary.attempted == 1
    assert summary.not_due == 1
    assert called == [(due_id, NOW)]
    with Session(engine) as db:
        assert db.get(FeedCursor, due_id).next_poll_at.replace(tzinfo=UTC) == (
            NOW + timedelta(minutes=30)
        )
        assert db.get(FeedCursor, future_id).next_poll_at.replace(tzinfo=UTC) == (
            NOW + timedelta(minutes=1)
        )

    restarted = asyncio.run(collect_due_sources(engine, collector, NOW))
    assert restarted.attempted == 0


def test_scheduler_prevents_overlapping_runs(tmp_path):
    async def scenario():
        engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
        add_source(engine, "due")
        entered = asyncio.Event()
        release = asyncio.Event()

        async def collector(source, now, validators):
            entered.set()
            await release.wait()
            return healthy(source)

        scheduler = RssScheduler(engine, collector, now=lambda: NOW, tick_seconds=0.01)
        first = asyncio.create_task(scheduler.run_once())
        await entered.wait()
        second = await scheduler.run_once()
        release.set()
        await first
        return second

    second = asyncio.run(scenario())
    assert second.overlap_skipped is True
    assert second.attempted == 0


def test_scheduler_stops_without_orphan_task(tmp_path):
    async def scenario():
        engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")

        async def collector(source, now, validators):
            return healthy(source)

        scheduler = RssScheduler(engine, collector, now=lambda: NOW, tick_seconds=0.01)
        task = scheduler.start()
        await asyncio.sleep(0)
        await scheduler.stop()
        return task

    task = asyncio.run(scenario())
    assert task.done()


def test_scheduler_cancels_blocked_collection_on_shutdown(tmp_path):
    async def scenario():
        engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
        add_source(engine, "blocked")
        entered = asyncio.Event()

        async def collector(source, now, validators):
            entered.set()
            await asyncio.Event().wait()

        scheduler = RssScheduler(engine, collector, now=lambda: NOW)
        task = scheduler.start()
        await entered.wait()
        await asyncio.wait_for(scheduler.stop(), timeout=0.1)
        return task

    task = asyncio.run(scenario())
    assert task.done()
    assert task.cancelled()


def test_scheduler_awaits_cooperative_sync_collector_shutdown(tmp_path):
    class BlockingCollector:
        def __init__(self):
            self.entered = threading.Event()
            self.release = threading.Event()

        def __call__(self, source, now, validators):
            self.entered.set()
            self.release.wait()
            return healthy(source)

        def cancel(self):
            self.release.set()

    async def scenario():
        engine = database(f"sqlite:///{tmp_path / 'vault.sqlite'}")
        add_source(engine, "blocked-sync")
        collector = BlockingCollector()
        scheduler = RssScheduler(engine, collector, now=lambda: NOW)
        task = scheduler.start()
        await asyncio.to_thread(collector.entered.wait)
        await asyncio.wait_for(scheduler.stop(), timeout=0.5)
        return task, collector

    task, collector = asyncio.run(scenario())
    assert collector.release.is_set()
    assert task.done()
    assert not task.cancelled()


def test_fastapi_lifespan_starts_and_awaits_scheduler(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("SYOSINT_RSS_SCHEDULER", raising=False)
    app = create_app(
        f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / "exports"
    )

    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        assert client.get("/sources").status_code == 200
        task = app.state.rss_scheduler._task

    assert task.done()
