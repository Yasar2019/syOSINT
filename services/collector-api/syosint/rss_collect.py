from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import random
import time
from typing import Literal, Protocol

from .rss_parse import parse_feed
from .rss_public import PublicWire
from .rss_types import FeedSource, NormalizedFeedItem, QuarantinedItem
from .safe_http import FeedFetchError, FetchResult, HttpValidators


class FeedClient(Protocol):
    def fetch(
        self, url: str, validators: HttpValidators | None = None
    ) -> FetchResult: ...


@dataclass(frozen=True)
class SourceOutcome:
    source_id: str
    status: Literal["healthy", "not-modified", "delayed"]
    items: tuple[NormalizedFeedItem, ...]
    error_category: str | None
    validators: HttpValidators | None
    quarantined: tuple[QuarantinedItem, ...] = ()


@dataclass(frozen=True)
class CollectionResult:
    sources: tuple[FeedSource, ...]
    outcomes: tuple[SourceOutcome, ...]


def _collect_source(
    source: FeedSource,
    now: datetime,
    client: FeedClient,
    validators: HttpValidators | None = None,
) -> SourceOutcome:
    for attempt in range(3):
        try:
            fetched = client.fetch(source.feed_url, validators)
            updated_validators = HttpValidators(
                etag=(fetched.validators.etag if fetched.validators else None)
                or (validators.etag if validators else None),
                last_modified=(
                    fetched.validators.last_modified if fetched.validators else None
                )
                or (validators.last_modified if validators else None),
            )
            if fetched.status_code == 304:
                return SourceOutcome(
                    source.id, "not-modified", (), None, updated_validators
                )
            parsed = parse_feed(source, fetched.content, now)
            return SourceOutcome(
                source.id,
                "healthy",
                parsed.items,
                None,
                updated_validators,
                parsed.quarantined,
            )
        except FeedFetchError as error:
            if not error.retryable or attempt == 2:
                return SourceOutcome(
                    source.id, "delayed", (), error.category, None
                )
            delay = (
                min(error.retry_after, 30.0)
                if error.retry_after is not None
                else min(float(2**attempt) * random.uniform(0.8, 1.2), 30.0)
            )
            time.sleep(delay)
        except (ValueError, OSError) as error:
            return SourceOutcome(
                source.id,
                "delayed",
                (),
                type(error).__name__.casefold(),
                None,
            )
    raise AssertionError("retry loop must return")


def collect_sources(
    sources: Sequence[FeedSource],
    previous: PublicWire | None,
    now: datetime,
    client: FeedClient,
    validators: Mapping[str, HttpValidators] | None = None,
) -> CollectionResult:
    del previous
    enabled = tuple(source for source in sources if source.enabled)
    return CollectionResult(
        enabled,
        tuple(
            _collect_source(
                source,
                now,
                client,
                validators.get(source.id) if validators else None,
            )
            for source in enabled
        ),
    )
