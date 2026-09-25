from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from hashlib import sha256
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException

from .rss_normalize import canonicalize_url, fingerprint_item
from .rss_types import (
    FeedSource,
    NormalizedFeedItem,
    ParseResult,
    QuarantinedItem,
)


MAX_FEED_ENTRIES = 200
XML_BASE = "{http://www.w3.org/XML/1998/namespace}base"


class _HeadlineTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def _clean_headline(value: str) -> str:
    parser = _HeadlineTextExtractor()
    parser.feed(unescape(value))
    parser.close()
    return " ".join("".join(parser.parts).split())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    return next((child for child in element if _local_name(child.tag) == name), None)


def _text(element: ElementTree.Element, name: str) -> str | None:
    child = _child(element, name)
    if child is None:
        return None
    value = "".join(child.itertext()).strip()
    return value or None


def _published_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _atom_link(entry: ElementTree.Element) -> str | None:
    links = [child for child in entry if _local_name(child.tag) == "link"]
    preferred = next(
        (link for link in links if link.attrib.get("rel", "alternate") == "alternate"),
        links[0] if links else None,
    )
    return preferred.attrib.get("href") if preferred is not None else None


def parse_feed(
    source: FeedSource, content: bytes, collected_at: datetime
) -> ParseResult:
    try:
        root = ElementTree.fromstring(content, forbid_dtd=True, forbid_entities=True)
    except (DefusedXmlException, ElementTree.ParseError) as error:
        raise ValueError("unsafe or invalid XML") from error

    root_name = _local_name(root.tag)
    if root_name == "rss":
        entries = [element for element in root.iter() if _local_name(element.tag) == "item"]
        is_atom = False
    elif root_name == "feed":
        entries = [element for element in root if _local_name(element.tag) == "entry"]
        is_atom = True
    else:
        raise ValueError("unsupported feed format")

    normalized: list[NormalizedFeedItem] = []
    quarantined: list[QuarantinedItem] = []
    root_base = root.attrib.get(XML_BASE, source.feed_url)

    for entry in entries[:MAX_FEED_ENTRIES]:
        raw = ElementTree.tostring(entry, encoding="utf-8")
        raw_digest = sha256(raw).hexdigest()
        native_id = _text(entry, "id" if is_atom else "guid")
        raw_headline = _text(entry, "title")
        headline = _clean_headline(raw_headline or "")
        raw_url = _atom_link(entry) if is_atom else _text(entry, "link")

        if not headline:
            quarantined.append(
                QuarantinedItem(source.id, "missing-headline", raw_digest, native_id)
            )
            continue
        if not raw_url:
            quarantined.append(
                QuarantinedItem(
                    source.id, "missing-url", raw_digest, native_id, headline
                )
            )
            continue
        entry_base = entry.attrib.get(XML_BASE, root_base)
        url = canonicalize_url(urljoin(entry_base, raw_url.strip()))
        raw_date = _text(entry, "updated" if is_atom else "pubDate")
        if is_atom and raw_date is None:
            raw_date = _text(entry, "published")
        published_at = _published_at(raw_date) or collected_at
        if published_at > collected_at + timedelta(hours=24):
            quarantined.append(
                QuarantinedItem(
                    source.id,
                    "future-published-at",
                    raw_digest,
                    native_id,
                    headline,
                )
            )
            continue

        normalized.append(
            NormalizedFeedItem(
                source_id=source.id,
                native_id=native_id,
                headline=headline,
                url=url,
                published_at=published_at,
                collected_at=collected_at,
                fingerprint=fingerprint_item(
                    source.id, native_id, url, headline, published_at
                ),
                raw_digest=raw_digest,
            )
        )

    return ParseResult(tuple(normalized), tuple(quarantined))
