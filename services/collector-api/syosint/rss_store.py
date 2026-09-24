from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import record
from .models import FeedCursor, FeedItem, FeedQuarantine, Source
from .rss_collect import SourceOutcome


@dataclass(frozen=True)
class StoreSummary:
    created: int
    duplicates: int
    quarantined: int


def store_collection(
    db: Session,
    source: Source,
    outcome: SourceOutcome,
    now: datetime,
) -> StoreSummary:
    created = 0
    duplicates = 0
    quarantine_created = 0
    cursor = db.get(FeedCursor, source.id)
    if cursor is None:
        cursor = FeedCursor(source_id=source.id)
        db.add(cursor)

    before_status = cursor.last_status
    cursor.last_attempt_at = now
    cursor.next_poll_at = now + timedelta(minutes=source.poll_interval_minutes)
    cursor.last_status = outcome.status
    if outcome.status == "delayed":
        cursor.consecutive_failures = (cursor.consecutive_failures or 0) + 1
        cursor.last_error_category = outcome.error_category
    else:
        cursor.consecutive_failures = 0
        cursor.last_error_category = None
        cursor.last_success_at = now
        if outcome.validators is not None:
            cursor.etag = outcome.validators.etag
            cursor.last_modified = outcome.validators.last_modified

    for item in outcome.items:
        existing = db.scalar(
            select(FeedItem).where(
                FeedItem.source_id == source.id,
                FeedItem.fingerprint == item.fingerprint,
            )
        )
        if existing is not None:
            duplicates += 1
            duplicate_fingerprint = sha256(
                f"duplicate\0{item.fingerprint}\0{item.raw_digest}".encode()
            ).hexdigest()
            duplicate = db.scalar(
                select(FeedItem).where(
                    FeedItem.source_id == source.id,
                    FeedItem.fingerprint == duplicate_fingerprint,
                )
            )
            if duplicate is None:
                db.add(
                    FeedItem(
                        source_id=source.id,
                        fingerprint=duplicate_fingerprint,
                        native_id=item.native_id,
                        headline=item.headline,
                        url=item.url,
                        text=item.headline,
                        published_at=item.published_at,
                        collected_at=item.collected_at,
                        raw_digest=item.raw_digest,
                        status="duplicate",
                    )
                )
            continue
        db.add(
            FeedItem(
                source_id=source.id,
                fingerprint=item.fingerprint,
                native_id=item.native_id,
                headline=item.headline,
                url=item.url,
                text=item.headline,
                published_at=item.published_at,
                collected_at=item.collected_at,
                raw_digest=item.raw_digest,
                status="new",
            )
        )
        created += 1

    for item in outcome.quarantined:
        existing = db.scalar(
            select(FeedQuarantine).where(
                FeedQuarantine.source_id == source.id,
                FeedQuarantine.raw_digest == item.raw_digest,
                FeedQuarantine.reason == item.reason,
            )
        )
        if existing is not None:
            continue
        db.add(
            FeedQuarantine(
                source_id=source.id,
                reason=item.reason,
                raw_digest=item.raw_digest,
                native_id=item.native_id,
                headline=item.headline,
                created_at=now,
            )
        )
        quarantine_created += 1

    health_changed = (
        outcome.status == "delayed" and before_status != "delayed"
    ) or (before_status == "delayed" and outcome.status != "delayed")
    if health_changed:
        record(
            db,
            "feed.health_changed",
            "source",
            source.id,
            before={"status": before_status},
            after={
                "status": outcome.status,
                "error_category": outcome.error_category,
            },
        )

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return StoreSummary(created, duplicates, quarantine_created)
