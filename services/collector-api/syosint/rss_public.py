from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from .rss_types import FeedSource


@dataclass(frozen=True)
class PublicWireEntry:
    id: str
    source_id: str
    source_label: Mapping[str, str]
    language: Literal["en", "ar"]
    headline: str
    url: str
    published_at: datetime
    collected_at: datetime


@dataclass(frozen=True)
class PublicWire:
    generated_at: datetime
    last_successful_refresh_at: datetime
    healthy_sources: int
    delayed_sources: int
    entries: tuple[PublicWireEntry, ...]


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _entry_dict(entry: PublicWireEntry) -> dict:
    return {
        "id": entry.id,
        "sourceId": entry.source_id,
        "sourceLabel": {
            "en": entry.source_label["en"],
            "ar": entry.source_label["ar"],
        },
        "language": entry.language,
        "headline": entry.headline,
        "url": entry.url,
        "publishedAt": _iso(entry.published_at),
        "collectedAt": _iso(entry.collected_at),
    }


def _fresh_entry(source: FeedSource, item) -> PublicWireEntry:
    return PublicWireEntry(
        id=f"{source.id}:{item.fingerprint}",
        source_id=source.id,
        source_label=source.label,
        language=source.language,
        headline=item.headline,
        url=item.url,
        published_at=item.published_at,
        collected_at=item.collected_at,
    )


def build_public_wire(result, previous: PublicWire | None, now: datetime) -> dict:
    cutoff = now - timedelta(days=7)
    sources = {source.id: source for source in result.sources}
    entries = {
        entry.id: entry
        for entry in (previous.entries if previous else ())
        if entry.published_at >= cutoff and entry.source_id in sources
    }
    for outcome in result.outcomes:
        source = sources[outcome.source_id]
        for item in outcome.items:
            if item.published_at < cutoff:
                continue
            fresh = _fresh_entry(source, item)
            entries[fresh.id] = fresh

    ordered = sorted(
        entries.values(),
        key=lambda item: (item.published_at, item.collected_at, item.id),
        reverse=True,
    )[:500]
    healthy = sum(
        outcome.status in {"healthy", "not-modified"}
        for outcome in result.outcomes
    )
    delayed = sum(outcome.status == "delayed" for outcome in result.outcomes)
    successful = healthy > 0
    last_success = (
        now
        if successful
        else previous.last_successful_refresh_at
        if previous
        else now
    )
    return {
        "schemaVersion": "1.0.0",
        "generatedAt": _iso(now),
        "lastSuccessfulRefreshAt": _iso(last_success),
        "sources": {"healthy": healthy, "delayed": delayed},
        "entries": [_entry_dict(entry) for entry in ordered],
    }


def public_wire_from_dict(value: Mapping) -> PublicWire:
    def parse_timestamp(timestamp: str) -> datetime:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    return PublicWire(
        generated_at=parse_timestamp(value["generatedAt"]),
        last_successful_refresh_at=parse_timestamp(
            value["lastSuccessfulRefreshAt"]
        ),
        healthy_sources=value["sources"]["healthy"],
        delayed_sources=value["sources"]["delayed"],
        entries=tuple(
            PublicWireEntry(
                id=entry["id"],
                source_id=entry["sourceId"],
                source_label=entry["sourceLabel"],
                language=entry["language"],
                headline=entry["headline"],
                url=entry["url"],
                published_at=parse_timestamp(entry["publishedAt"]),
                collected_at=parse_timestamp(entry["collectedAt"]),
            )
            for entry in value["entries"]
        ),
    )
