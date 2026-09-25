from datetime import UTC, datetime, timedelta
import json

import pytest

from syosint.rss_collect import CollectionResult, SourceOutcome, collect_sources
from syosint.rss_public import (
    PublicWire,
    PublicWireEntry,
    build_public_wire,
    public_wire_from_dict,
)
from syosint.rss_types import FeedSource, NormalizedFeedItem
from syosint.safe_http import FeedFetchError, FetchResult, HttpValidators


NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
PUBLIC_KEYS = {
    "id",
    "sourceId",
    "sourceLabel",
    "language",
    "headline",
    "url",
    "publishedAt",
    "collectedAt",
}


def source(source_id):
    return FeedSource(
        id=source_id,
        label={"en": source_id.title(), "ar": f"مصدر {source_id}"},
        feed_url=f"https://{source_id}.example/rss",
        homepage_url=f"https://{source_id}.example/",
        language="en",
        enabled=True,
        required_terms=("Syria",),
        attribution=f"{source_id.title()} attribution",
        attribution_url=f"https://{source_id}.example/legal",
    )


HEALTHY = source("healthy")
FAILING = source("failing")
PREVIOUS = PublicWire(
    generated_at=NOW - timedelta(minutes=30),
    last_successful_refresh_at=NOW - timedelta(minutes=30),
    healthy_sources=2,
    delayed_sources=0,
    entries=(
        PublicWireEntry(
            id="failing:old",
            source_id="failing",
            source_label=FAILING.label,
            language="en",
            headline="Previous Syria report",
            url="https://failing.example/old",
            published_at=NOW - timedelta(hours=1),
            collected_at=NOW - timedelta(minutes=30),
        ),
    ),
)


def rss(item_id="fresh", title="Fresh Syria report"):
    return f"""<?xml version='1.0'?><rss version='2.0'><channel><item>
      <guid>{item_id}</guid><title>{title}</title>
      <link>https://healthy.example/{item_id}</link>
      <pubDate>Wed, 23 Sep 2026 15:55:00 +0000</pubDate>
    </item></channel></rss>""".encode()


class StubClient:
    def __init__(self, results):
        self.results = {key: list(value) for key, value in results.items()}
        self.calls = []

    def fetch(self, url, validators=None):
        self.calls.append((url, validators))
        result = self.results[url].pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def fetched(content):
    return FetchResult(200, content, HttpValidators(etag='"v1"'))


def test_partial_success_keeps_current_previous_entries():
    client = StubClient(
        {
            HEALTHY.feed_url: [fetched(rss())],
            FAILING.feed_url: [FeedFetchError("timeout", retryable=False)],
        }
    )

    result = collect_sources(
        [HEALTHY, FAILING], previous=PREVIOUS, now=NOW, client=client
    )
    wire = build_public_wire(result, PREVIOUS, NOW)

    assert {item["sourceId"] for item in wire["entries"]} == {
        "healthy",
        "failing",
    }
    assert all(set(item) == PUBLIC_KEYS for item in wire["entries"])
    assert wire["sources"] == {"configured": 2, "healthy": 1, "delayed": 1}


def test_retries_only_retryable_failures_at_most_three_times(monkeypatch):
    monkeypatch.setattr("syosint.rss_collect.time.sleep", lambda _seconds: None)
    retryable = FeedFetchError("busy", status_code=503, retryable=True)
    client = StubClient(
        {HEALTHY.feed_url: [retryable, retryable, fetched(rss())]}
    )

    result = collect_sources([HEALTHY], previous=None, now=NOW, client=client)

    assert result.outcomes[0].status == "healthy"
    assert len(client.calls) == 3


def test_honors_bounded_retry_after(monkeypatch):
    delays = []
    monkeypatch.setattr("syosint.rss_collect.time.sleep", delays.append)
    client = StubClient(
        {
            HEALTHY.feed_url: [
                FeedFetchError(
                    "rate-limited",
                    status_code=429,
                    retry_after=120,
                    retryable=True,
                ),
                fetched(rss()),
            ]
        }
    )

    collect_sources([HEALTHY], previous=None, now=NOW, client=client)

    assert delays == [30]


def test_adds_jitter_to_exponential_retry_delay(monkeypatch):
    delays = []
    monkeypatch.setattr("syosint.rss_collect.time.sleep", delays.append)
    monkeypatch.setattr("syosint.rss_collect.random.uniform", lambda _low, _high: 1.1)
    client = StubClient(
        {
            HEALTHY.feed_url: [
                FeedFetchError("timeout", retryable=True),
                fetched(rss()),
            ]
        }
    )

    collect_sources([HEALTHY], previous=None, now=NOW, client=client)

    assert delays == [1.1]


def test_public_wire_expires_old_entries_deduplicates_and_caps_at_100_per_source():
    recent = tuple(
        PublicWireEntry(
            id=f"healthy:{index}",
            source_id="healthy",
            source_label=HEALTHY.label,
            language="en",
            headline=f"Syria report {index}",
            url=f"https://healthy.example/{index}",
            published_at=NOW - timedelta(minutes=index),
            collected_at=NOW,
        )
        for index in range(510)
    )
    old = PublicWireEntry(
        id="healthy:expired",
        source_id="healthy",
        source_label=HEALTHY.label,
        language="en",
        headline="Expired Syria report",
        url="https://healthy.example/expired",
        published_at=NOW - timedelta(days=8),
        collected_at=NOW - timedelta(days=8),
    )
    previous = PublicWire(NOW, NOW, 1, 0, recent + (old, recent[0]))
    client = StubClient({HEALTHY.feed_url: [FetchResult(304, b"", None)]})

    result = collect_sources([HEALTHY], previous=previous, now=NOW, client=client)
    wire = build_public_wire(result, previous, NOW)

    assert len(wire["entries"]) == 100
    assert len({entry["id"] for entry in wire["entries"]}) == 100
    assert wire["sourceStates"][0]["entryCount"] == 100
    assert "healthy:expired" not in {entry["id"] for entry in wire["entries"]}


def test_projects_empty_and_delayed_sources_without_private_failure_details():
    empty = source("empty")
    delayed = source("delayed")
    result = CollectionResult(
        (empty, delayed),
        (
            SourceOutcome("empty", "healthy", (), None, None),
            SourceOutcome("delayed", "delayed", (), "private-dns-message", None),
        ),
    )

    wire = build_public_wire(result, None, NOW)

    assert wire["schemaVersion"] == "1.1.0"
    assert wire["sources"] == {"configured": 2, "healthy": 1, "delayed": 1}
    assert wire["sourceStates"] == [
        {
            "id": "empty",
            "label": empty.label,
            "language": "en",
            "attribution": empty.attribution,
            "attributionUrl": empty.attribution_url,
            "status": "healthy",
            "lastSuccessfulRefreshAt": "2026-09-23T16:00:00Z",
            "entryCount": 0,
        },
        {
            "id": "delayed",
            "label": delayed.label,
            "language": "en",
            "attribution": delayed.attribution,
            "attributionUrl": delayed.attribution_url,
            "status": "delayed",
            "lastSuccessfulRefreshAt": None,
            "entryCount": 0,
        },
    ]
    assert "private-dns-message" not in json.dumps(wire)


def test_caps_each_source_newest_first_without_dropping_quiet_source():
    busy, quiet = source("busy"), source("quiet")

    def items(source_id, count):
        return tuple(
            NormalizedFeedItem(
                source_id,
                str(index),
                "Same Syria headline",
                f"https://{source_id}.example/{index}",
                NOW - timedelta(minutes=index),
                NOW,
                str(index),
                str(index),
            )
            for index in range(count)
        )

    result = CollectionResult(
        (busy, quiet),
        (
            SourceOutcome("busy", "healthy", items("busy", 130), None, None),
            SourceOutcome("quiet", "healthy", items("quiet", 2), None, None),
        ),
    )

    wire = build_public_wire(result, None, NOW)

    assert len(wire["entries"]) == 102
    assert [
        entry["id"] for entry in wire["entries"] if entry["sourceId"] == "busy"
    ] == [f"busy:{index}" for index in range(100)]
    assert [
        entry["id"] for entry in wire["entries"] if entry["sourceId"] == "quiet"
    ] == ["quiet:0", "quiet:1"]
    assert [(state["id"], state["entryCount"]) for state in wire["sourceStates"]] == [
        ("busy", 100),
        ("quiet", 2),
    ]


def test_applies_existing_global_500_limit_after_per_source_limit():
    sources = tuple(source(f"publisher-{index}") for index in range(6))
    previous = PublicWire(
        NOW,
        NOW,
        6,
        0,
        tuple(
            PublicWireEntry(
                f"{publisher.id}:{index}",
                publisher.id,
                publisher.label,
                "en",
                f"Syria headline {index}",
                f"https://{publisher.id}.example/{index}",
                NOW - timedelta(minutes=index),
                NOW,
            )
            for publisher in sources
            for index in range(110)
        ),
    )
    result = CollectionResult(
        sources,
        tuple(
            SourceOutcome(publisher.id, "not-modified", (), None, None)
            for publisher in sources
        ),
    )

    wire = build_public_wire(result, previous, NOW)

    assert len(wire["entries"]) == 500
    assert max(entry["publishedAt"] for entry in wire["entries"]) == "2026-09-23T16:00:00Z"
    assert min(entry["publishedAt"] for entry in wire["entries"]) == "2026-09-23T14:37:00Z"
    assert sum(state["entryCount"] for state in wire["sourceStates"]) == 500


def test_reads_previous_1_0_0_artifact_and_keeps_recent_entries():
    legacy = public_wire_from_dict(
        {
            "schemaVersion": "1.0.0",
            "generatedAt": "2026-09-23T15:30:00Z",
            "lastSuccessfulRefreshAt": "2026-09-23T15:30:00Z",
            "sources": {"healthy": 1, "delayed": 0},
            "entries": [
                {
                    "id": "failing:old",
                    "sourceId": "failing",
                    "sourceLabel": FAILING.label,
                    "language": "en",
                    "headline": "Previous Syria report",
                    "url": "https://failing.example/old",
                    "publishedAt": "2026-09-23T15:00:00Z",
                    "collectedAt": "2026-09-23T15:30:00Z",
                },
            ],
        }
    )
    result = CollectionResult(
        (FAILING,), (SourceOutcome("failing", "delayed", (), "timeout", None),),
    )

    wire = build_public_wire(result, legacy, NOW)

    assert [entry["id"] for entry in wire["entries"]] == ["failing:old"]
    assert wire["lastSuccessfulRefreshAt"] == "2026-09-23T15:30:00Z"
    assert wire["sourceStates"][0]["lastSuccessfulRefreshAt"] == "2026-09-23T15:30:00Z"
    assert wire["sourceStates"][0]["entryCount"] == 1


def test_all_delayed_preserves_previous_source_refresh_and_entries():
    previous = PublicWire(
        NOW - timedelta(minutes=30),
        NOW - timedelta(minutes=30),
        1,
        0,
        PREVIOUS.entries,
    )
    result = CollectionResult(
        (FAILING,), (SourceOutcome("failing", "delayed", (), "timeout", None),),
    )
    prior = public_wire_from_dict(
        build_public_wire(
            CollectionResult(
                (FAILING,), (SourceOutcome("failing", "healthy", (), None, None),)
            ),
            previous,
            NOW - timedelta(minutes=15),
        )
    )

    wire = build_public_wire(result, prior, NOW)

    assert wire["lastSuccessfulRefreshAt"] == "2026-09-23T15:45:00Z"
    assert [entry["id"] for entry in wire["entries"]] == ["failing:old"]
    assert wire["sourceStates"][0]["status"] == "delayed"
    assert wire["sourceStates"][0]["lastSuccessfulRefreshAt"] == "2026-09-23T15:45:00Z"
    assert wire["sourceStates"][0]["entryCount"] == 1


def test_public_wire_drops_previous_entries_from_removed_sources():
    client = StubClient({HEALTHY.feed_url: [fetched(rss())]})

    result = collect_sources([HEALTHY], previous=PREVIOUS, now=NOW, client=client)
    wire = build_public_wire(result, PREVIOUS, NOW)

    assert {entry["sourceId"] for entry in wire["entries"]} == {"healthy"}


def test_public_wire_rejects_old_items_from_fresh_fetch():
    old_feed = rss().replace(
        b"Wed, 23 Sep 2026 15:55:00 +0000",
        b"Tue, 01 Sep 2026 15:55:00 +0000",
    )
    client = StubClient({HEALTHY.feed_url: [fetched(old_feed)]})

    result = collect_sources([HEALTHY], previous=None, now=NOW, client=client)
    wire = build_public_wire(result, None, NOW)

    assert wire["entries"] == []


def test_collect_public_cli_writes_an_atomic_schema_valid_wire(tmp_path, monkeypatch):
    from syosint import rss_cli

    config = tmp_path / "sources.json"
    output = tmp_path / "news-wire.json"
    config.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0.0",
                "sources": [
                    {
                        "id": HEALTHY.id,
                        "label": HEALTHY.label,
                        "feedUrl": HEALTHY.feed_url,
                        "homepageUrl": HEALTHY.homepage_url,
                        "language": HEALTHY.language,
                        "enabled": True,
                        "requiredTerms": list(HEALTHY.required_terms),
                        "attribution": HEALTHY.attribution,
                        "attributionUrl": HEALTHY.attribution_url,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    client = StubClient({HEALTHY.feed_url: [fetched(rss())]})
    monkeypatch.setattr(rss_cli, "SafeFeedClient", lambda *args, **kwargs: client)

    assert rss_cli.main(
        ["collect-public", "--config", str(config), "--output", str(output)]
    ) == 0

    value = json.loads(output.read_text(encoding="utf-8"))
    rss_cli._validate_wire(value)
    assert value["entries"][0]["headline"] == "Fresh Syria report"
    assert list(tmp_path.glob("tmp*")) == []


def test_collect_public_cli_fails_closed_when_every_source_is_delayed(
    tmp_path, monkeypatch
):
    from syosint import rss_cli

    config = tmp_path / "sources.json"
    output = tmp_path / "news-wire.json"
    config.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0.0",
                "sources": [
                    {
                        "id": HEALTHY.id,
                        "label": HEALTHY.label,
                        "feedUrl": HEALTHY.feed_url,
                        "homepageUrl": HEALTHY.homepage_url,
                        "language": HEALTHY.language,
                        "enabled": True,
                        "requiredTerms": list(HEALTHY.required_terms),
                        "attribution": HEALTHY.attribution,
                        "attributionUrl": HEALTHY.attribution_url,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    client = StubClient(
        {HEALTHY.feed_url: [FeedFetchError("dns-failure", retryable=False)]}
    )
    monkeypatch.setattr(rss_cli, "SafeFeedClient", lambda *args, **kwargs: client)

    with pytest.raises(RuntimeError, match="every enabled RSS source is delayed"):
        rss_cli.main(
            ["collect-public", "--config", str(config), "--output", str(output)]
        )

    assert not output.exists()


@pytest.mark.parametrize(
    "result",
    [
        FeedFetchError("timeout", retryable=True),
        FetchResult(200, b"not-json", None),
        FetchResult(200, b"{}", None),
    ],
)
def test_previous_wire_failure_falls_back_to_fresh_collection(monkeypatch, result):
    from syosint import rss_cli

    client = StubClient({"https://pages.example/news-wire.json": [result]})
    monkeypatch.setattr(rss_cli, "SafeFeedClient", lambda *args, **kwargs: client)

    assert rss_cli._load_previous("https://pages.example/news-wire.json") is None
