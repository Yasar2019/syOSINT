from datetime import UTC, datetime
from pathlib import Path

import pytest

from syosint.rss_normalize import canonicalize_url, fingerprint_item, matches_topic
from syosint.rss_parse import parse_feed
from syosint.rss_types import FeedSource


NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)
FIXTURES = Path(__file__).parent / "fixtures"
ARABIC_SOURCE = FeedSource(
    id="arabic-source",
    label={"en": "Arabic source", "ar": "مصدر عربي"},
    feed_url="https://example.org/feed.xml",
    homepage_url="https://example.org/",
    language="ar",
    enabled=True,
    required_terms=("سوريا", "سوري", "سورية"),
)
ENGLISH_SOURCE = FeedSource(
    id="english-source",
    label={"en": "English source", "ar": "مصدر إنجليزي"},
    feed_url="https://example.org/feed.xml",
    homepage_url="https://example.org/",
    language="en",
    enabled=True,
    required_terms=("Syria", "Syrian"),
)


def test_parses_rss_and_applies_arabic_topic_terms():
    result = parse_feed(ARABIC_SOURCE, (FIXTURES / "rss.xml").read_bytes(), NOW)

    assert [item.headline for item in result.items] == ["تطور جديد في سوريا"]
    assert result.items[0].url == "https://example.org/reports/1"
    assert result.items[0].published_at == datetime(
        2026, 9, 23, 15, 55, tzinfo=UTC
    )
    assert result.quarantined == ()


def test_parses_atom_relative_links_and_falls_back_for_an_invalid_date():
    result = parse_feed(ENGLISH_SOURCE, (FIXTURES / "atom.xml").read_bytes(), NOW)

    assert len(result.items) == 1
    assert result.items[0].headline == "Syria & regional update"
    assert result.items[0].url == "https://example.org/news/reports/3?view=full"
    assert result.items[0].published_at == NOW
    assert result.items[0].native_id is None


def test_identity_prefers_native_id_then_url_then_content():
    assert fingerprint_item(
        "s", "native-1", "https://e.org/a", "Title", NOW
    ) == fingerprint_item(
        "s", "native-1", "https://e.org/changed", "Changed", NOW
    )
    assert fingerprint_item(
        "s", None, "https://e.org/a?utm_source=x", "Title", NOW
    ) == fingerprint_item("s", None, "https://e.org/a", "Changed", NOW)
    assert fingerprint_item("s", None, "", "Title", NOW) != fingerprint_item(
        "s", None, "", "Changed", NOW
    )


def test_canonicalization_removes_only_explicit_tracking_keys():
    assert canonicalize_url(
        "https://Example.org:443/a?utm_campaign=x&view=full&fbclid=y#part"
    ) == "https://example.org/a?view=full"
    assert canonicalize_url("http://Example.org:80/a?b=2&a=1") == (
        "http://example.org/a?b=2&a=1"
    )


def test_topic_matching_normalizes_unicode_and_case():
    assert matches_topic("SYRIAN UPDATE", ("Syrian",))
    assert matches_topic("تطورات سُورِيَّة", ("سُورِيَّة",))
    assert not matches_topic("Regional update", ("Syria",))


def test_far_future_date_is_quarantined():
    content = b"""<?xml version='1.0'?>
    <rss version='2.0'><channel><item>
      <guid>future-1</guid><title>Syria future report</title>
      <link>https://example.org/future</link>
      <pubDate>Fri, 25 Sep 2026 16:01:00 +0000</pubDate>
    </item></channel></rss>"""

    result = parse_feed(ENGLISH_SOURCE, content, NOW)

    assert result.items == ()
    assert result.quarantined[0].reason == "future-published-at"


def test_rejects_dtd_and_entity_payloads():
    content = b"""<?xml version='1.0'?>
    <!DOCTYPE rss [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]>
    <rss version='2.0'><channel><item><title>&xxe;</title></item></channel></rss>"""

    with pytest.raises(ValueError, match="unsafe or invalid XML"):
        parse_feed(ENGLISH_SOURCE, content, NOW)
