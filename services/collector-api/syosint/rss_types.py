from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Mapping


@dataclass(frozen=True)
class FeedSource:
    id: str
    label: Mapping[str, str]
    feed_url: str
    homepage_url: str
    language: Literal["en", "ar"]
    enabled: bool
    required_terms: tuple[str, ...]
    attribution: str | None = None
    attribution_url: str | None = None
    topic_mode: Literal["syria-only", "keyword-filtered"] = "keyword-filtered"
    excluded_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class NormalizedFeedItem:
    source_id: str
    native_id: str | None
    headline: str
    url: str
    published_at: datetime
    collected_at: datetime
    fingerprint: str
    raw_digest: str


@dataclass(frozen=True)
class QuarantinedItem:
    source_id: str
    reason: str
    raw_digest: str
    native_id: str | None = None
    headline: str | None = None


@dataclass(frozen=True)
class ParseResult:
    items: tuple[NormalizedFeedItem, ...]
    quarantined: tuple[QuarantinedItem, ...]
