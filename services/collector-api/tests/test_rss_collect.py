from datetime import UTC, datetime
from pathlib import Path

from syosint.rss_collect import collect_sources, headline_matches
from syosint.rss_types import FeedSource
from syosint.safe_http import FetchResult, HttpValidators


NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
RSS = Path(__file__).parent / "fixtures" / "rss.xml"


def source(
    *, topic_mode="keyword-filtered", required_terms=("سوريا",), excluded_terms=()
):
    return FeedSource(
        id="topic-source",
        label={"en": "Topic source", "ar": "مصدر"},
        feed_url="https://example.org/feed.xml",
        homepage_url="https://example.org/",
        language="ar",
        enabled=True,
        topic_mode=topic_mode,
        required_terms=required_terms,
        excluded_terms=excluded_terms,
    )


def test_topic_modes_are_deterministic():
    assert headline_matches(source(topic_mode="syria-only"), "Any headline")
    filtered = source(required_terms=("syria",), excluded_terms=("football",))
    assert headline_matches(filtered, "Syria humanitarian update")
    assert not headline_matches(filtered, "Syria football result")
    assert not headline_matches(filtered, "Regional update")
    assert not headline_matches(
        source(topic_mode="syria-only", excluded_terms=("football",)),
        "Football result",
    )


def test_topic_matching_normalizes_unicode_and_case():
    assert headline_matches(source(required_terms=("Syrian",)), "SYRIAN UPDATE")
    assert headline_matches(source(required_terms=("سُورِيَّة",)), "تطورات سُورِيَّة")
    assert not headline_matches(source(excluded_terms=("سُورِيَّة",)), "سُورِيَّة")


def test_collection_applies_topic_policy_after_parsing():
    class Client:
        def fetch(self, url, validators=None):
            return FetchResult(200, RSS.read_bytes(), HttpValidators(etag='"v1"'))

    filtered = collect_sources((source(),), None, NOW, Client())
    unfiltered = collect_sources(
        (source(topic_mode="syria-only"),), None, NOW, Client()
    )

    assert [item.headline for item in filtered.outcomes[0].items] == [
        "تطور جديد في سوريا"
    ]
    assert [item.headline for item in unfiltered.outcomes[0].items] == [
        "تطور جديد في سوريا",
        "خبر إقليمي لا يتعلق بالموضوع",
    ]
