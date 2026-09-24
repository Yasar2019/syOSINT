"""Local API harness with a deterministic synthetic feed for browser tests."""

import os
from pathlib import Path

import uvicorn

import syosint.api as api_module
from syosint.api import create_app
from syosint.rss_collect import SourceOutcome
from syosint.rss_types import NormalizedFeedItem
from syosint.safe_http import HttpValidators


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


def main():
    root = Path(__file__).resolve().parents[3]
    database_path = Path(
        os.environ.get(
            "SYOSINT_DB_PATH", str(root / "private-data/syosint-browser.sqlite3")
        )
    )
    database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    api_module.default_collector = synthetic_collector
    app = create_app(
        f"sqlite:///{database_path}",
        Path(os.environ.get("SYOSINT_EXPORT_DIR", str(root / "pending-exports"))),
    )
    uvicorn.run(app, host="127.0.0.1", port=8765)


if __name__ == "__main__":
    main()
