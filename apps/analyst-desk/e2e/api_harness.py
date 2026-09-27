"""Local API harness with a deterministic synthetic feed for browser tests."""

import os
from datetime import datetime, timezone
from pathlib import Path

import uvicorn

import syosint.api as api_module
from syosint.api import create_app
from syosint.rss_collect import SourceOutcome
from syosint.rss_types import NormalizedFeedItem
from syosint.safe_http import HttpValidators
from syosint.telegram_types import ResolvedPublicChannel, TelegramMessage


def synthetic_collector(source, collected_at, validators):
    item = NormalizedFeedItem(
        source_id=str(source.id),
        native_id="browser-fixture-1",
        headline="Synthetic Syria feed report",
        url="https://feed.example/reports/browser-fixture-1",
        published_at=collected_at,
        collected_at=collected_at,
        fingerprint="browser-fixture-fingerprint",
        raw_digest="b" * 64,
    )
    return SourceOutcome(
        str(source.id),
        "healthy",
        (item,),
        None,
        HttpValidators(etag='"browser-v1"'),
    )


class SyntheticPublicTransport:
    """Network-free, public-only fixture for browser verification."""

    async def is_authorized(self):
        return True

    async def disconnect(self):
        return None

    async def resolve_username(self, username):
        return ResolvedPublicChannel(42, "publicnews", "Synthetic Public News", True)

    async def iter_messages(self, channel_id, *, limit, since):
        yield TelegramMessage(1, "<img src=x onerror=alert(1)> Synthetic local post", datetime.now(timezone.utc))

    async def reconcile_messages(self, channel_id, native_ids):
        return tuple(TelegramMessage(1, "<img src=x onerror=alert(1)> Synthetic local post", datetime.now(timezone.utc)) for native_id in native_ids if native_id == "1")

    async def iter_media_chunks(self, channel_id, message_id):
        if False:
            yield b""


def main():
    root = Path(__file__).resolve().parents[3]
    database_path = Path(
        os.environ.get(
            "SYOSINT_DB_PATH", str(root / "private-data/syosint-browser.sqlite3")
        )
    )
    database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    api_module.default_collector = synthetic_collector
    os.environ["SYOSINT_TELEGRAM_API_ID"] = "12345"
    os.environ["SYOSINT_TELEGRAM_API_HASH"] = "synthetic-browser-fixture"
    os.environ["SYOSINT_TELEGRAM_SCHEDULER"] = "0"
    app = create_app(
        f"sqlite:///{database_path}",
        Path(os.environ.get("SYOSINT_EXPORT_DIR", str(root / "pending-exports"))),
    )
    app.state.telegram_transport_factory = SyntheticPublicTransport
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
