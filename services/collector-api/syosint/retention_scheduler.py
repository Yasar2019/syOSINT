"""One-process daily retention scheduler; work is synchronous and bounded.

No executor thread can outlive lifespan shutdown. A local bounded run completes
before the event loop handles shutdown; multiple API workers are unsupported.
"""
import asyncio
from datetime import UTC, datetime
from .retention import run_retention


class RetentionScheduler:
    def __init__(self, engine, media_root, *, apply=False, now=lambda: datetime.now(UTC), tick_seconds=86400):
        self.engine = engine; self.media_root = media_root; self.apply = apply
        self.now = now; self.tick_seconds = tick_seconds
        self._stop = asyncio.Event(); self._task = None; self._running = False

    async def run_once(self):
        if self._running:
            return None
        self._running = True
        try:
            return run_retention(self.engine,self.media_root,self.now(),apply=self.apply)
        finally:
            self._running = False

    async def _run(self):
        while not self._stop.is_set():
            try:
                await self.run_once()
            except Exception:
                # No raw database/filesystem errors or private strings in logs.
                pass
            try:
                await asyncio.wait_for(self._stop.wait(),timeout=self.tick_seconds)
            except TimeoutError:
                pass

    def start(self):
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = asyncio.create_task(self._run(),name='syosint-retention-scheduler')
        return self._task

    async def stop(self):
        self._stop.set()
        if self._task is not None:
            await self._task
