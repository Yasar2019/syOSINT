from datetime import UTC, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from syosint.db import database
from syosint.models import IntakeItem, Source, TelegramCursor
from syosint.telegram_scheduler import TelegramScheduler
from syosint.telegram_session import TelegramSettings

from test_telegram_collect import FakeTransport, NOW, message


@pytest.mark.asyncio
async def test_failure_isolated_to_one_approved_channel(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'intake.sqlite'}")
    with Session(engine) as db:
        for username in ("brokennews", "publicnews"):
            db.add(Source(name=username, url=f"https://t.me/{username}", kind="telegram",
                          public_identifier=username, language="en", enabled=True))
            db.flush()
            db.add(TelegramCursor(source_id=db.scalar(select(Source.id).where(Source.public_identifier == username)), channel_id=42))
        db.commit()
    started = []

    def factory():
        class Transport(FakeTransport):
            async def disconnect(self):
                pass

        if not started:
            result = Transport(username="brokennews", failure=RuntimeError("synthetic-secret"))
        else:
            result = Transport([message(1)], username="publicnews")
        started.append(result)
        return result

    scheduler = TelegramScheduler(engine, TelegramSettings(123, "synthetic", tmp_path), factory=factory)
    await scheduler.poll_once(NOW)
    with Session(engine) as db:
        assert db.get(TelegramCursor, 1).last_status == "delayed"
        assert db.get(TelegramCursor, 1).last_error_category == "collection-failed"
        assert db.get(TelegramCursor, 2).last_status == "healthy"
        assert len(db.scalars(select(IntakeItem)).all()) == 1
    assert len(started) == 2


@pytest.mark.asyncio
async def test_rate_limit_pauses_only_affected_channel(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'intake.sqlite'}")
    with Session(engine) as db:
        db.add(Source(name="Public", url="https://t.me/publicnews", kind="telegram",
                      public_identifier="publicnews", language="en", enabled=True))
        db.flush()
        db.add(TelegramCursor(source_id=db.scalar(select(Source.id).where(Source.public_identifier == "publicnews")), channel_id=42))
        db.commit()

    class WaitError(Exception):
        seconds = 720

    class WaitingTransport(FakeTransport):
        async def disconnect(self):
            pass

    started = []

    def factory():
        started.append(True)
        return WaitingTransport(failure=WaitError("synthetic-secret"))

    scheduler = TelegramScheduler(engine, TelegramSettings(123, "synthetic", tmp_path), factory=factory)
    await scheduler.poll_once(NOW)
    await scheduler.poll_once(NOW + timedelta(minutes=2))
    with Session(engine) as db:
        cursor = db.get(TelegramCursor, 1)
        assert cursor.last_status == "delayed"
        assert cursor.last_error_category == "rate-limited"
        assert cursor.rate_limit_until.replace(tzinfo=UTC) == NOW + timedelta(seconds=720)
    assert len(started) == 1
