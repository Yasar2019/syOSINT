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
class PublicSourceState:
    id: str
    label: Mapping[str, str]
    language: Literal["en", "ar"]
    attribution: str
    attribution_url: str
    status: Literal["healthy", "not-modified", "delayed"]
    last_successful_refresh_at: datetime | None
    entry_count: int


@dataclass(frozen=True)
class PublicWire:
    generated_at: datetime
    last_successful_refresh_at: datetime
    healthy_sources: int
    delayed_sources: int
    entries: tuple[PublicWireEntry, ...]
    source_states: tuple[PublicSourceState, ...] = ()


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


def _source_state_dict(state: PublicSourceState) -> dict:
    return {
        "id": state.id,
        "label": {"en": state.label["en"], "ar": state.label["ar"]},
        "language": state.language,
        "attribution": state.attribution,
        "attributionUrl": state.attribution_url,
        "status": state.status,
        "lastSuccessfulRefreshAt": (
            _iso(state.last_successful_refresh_at)
            if state.last_successful_refresh_at is not None
            else None
        ),
        "entryCount": state.entry_count,
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


def build_public_wire(
    result, previous: PublicWire | None, now: datetime, per_source_limit: int = 100
) -> dict:
    cutoff = now - timedelta(days=7)
    sources = {source.id: source for source in result.sources if source.enabled}
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

    def newest_first(entry: PublicWireEntry):
        return (entry.published_at, entry.collected_at, entry.id)

    grouped: dict[str, list[PublicWireEntry]] = {source_id: [] for source_id in sources}
    for entry in entries.values():
        grouped[entry.source_id].append(entry)
    retained = [
        entry
        for group in grouped.values()
        for entry in sorted(group, key=newest_first, reverse=True)[:per_source_limit]
    ]
    ordered = sorted(retained, key=newest_first, reverse=True)[:500]
    entry_counts = {source_id: 0 for source_id in sources}
    for entry in ordered:
        entry_counts[entry.source_id] += 1
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
    previous_states = (
        {state.id: state for state in previous.source_states} if previous else {}
    )
    legacy_ids = {entry.source_id for entry in previous.entries} if previous else set()
    outcomes = {outcome.source_id: outcome for outcome in result.outcomes}
    source_states = []
    for source in sources.values():
        if source.attribution is None or source.attribution_url is None:
            raise ValueError("enabled public sources require attribution")
        status = outcomes[source.id].status
        prior_state = previous_states.get(source.id)
        prior_refresh = (
            prior_state.last_successful_refresh_at
            if prior_state is not None
            else previous.last_successful_refresh_at
            if previous is not None and source.id in legacy_ids
            else None
        )
        source_states.append(
            PublicSourceState(
                id=source.id,
                label=source.label,
                language=source.language,
                attribution=source.attribution,
                attribution_url=source.attribution_url,
                status=status,
                last_successful_refresh_at=now if status != "delayed" else prior_refresh,
                entry_count=entry_counts[source.id],
            )
        )
    return {
        "schemaVersion": "1.1.0",
        "generatedAt": _iso(now),
        "lastSuccessfulRefreshAt": _iso(last_success),
        "sources": {"configured": len(sources), "healthy": healthy, "delayed": delayed},
        "sourceStates": [_source_state_dict(state) for state in source_states],
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
        source_states=tuple(
            PublicSourceState(
                id=state["id"],
                label=state["label"],
                language=state["language"],
                attribution=state["attribution"],
                attribution_url=state["attributionUrl"],
                status=state["status"],
                last_successful_refresh_at=(
                    parse_timestamp(state["lastSuccessfulRefreshAt"])
                    if state["lastSuccessfulRefreshAt"] is not None
                    else None
                ),
                entry_count=state["entryCount"],
            )
            for state in value.get("sourceStates", ())
        ),
    )
