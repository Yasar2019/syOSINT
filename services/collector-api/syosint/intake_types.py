from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class NormalizedIntakeItem:
    platform: Literal["rss", "telegram"]
    native_id: str | None
    headline: str | None
    url: str
    text: str
    published_at: datetime
    edited_at: datetime | None
    collected_at: datetime
    fingerprint: str
    raw_digest: str


@dataclass(frozen=True)
class QuarantinedIntakeItem:
    platform: Literal["rss", "telegram"]
    reason: str
    raw_digest: str
    native_id: str | None = None
    headline: str | None = None


@dataclass(frozen=True)
class StoreSummary:
    created: int
    duplicates: int
    quarantined: int
