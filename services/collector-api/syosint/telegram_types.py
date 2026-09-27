"""Private, typed boundary for manually approved public Telegram channels."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ResolvedPublicChannel:
    channel_id: int
    username: str
    title: str
    public: bool


@dataclass(frozen=True)
class TelegramMessage:
    message_id: int
    text: str
    published_at: datetime
    edited_at: datetime | None = None


@dataclass(frozen=True)
class SyncSummary:
    created: int
    duplicates: int
    quarantined: int
    oldest_published_at: datetime | None
