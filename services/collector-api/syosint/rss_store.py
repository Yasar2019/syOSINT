from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .db import record
from .intake_store import store_intake_batch
from .intake_types import NormalizedIntakeItem, QuarantinedIntakeItem, StoreSummary
from .models import FeedCursor, Source
from .rss_collect import SourceOutcome


def store_collection(
    db: Session,
    source: Source,
    outcome: SourceOutcome,
    now: datetime,
) -> StoreSummary:
    def update_cursor(session: Session) -> None:
        cursor = session.get(FeedCursor, source.id)
        if cursor is None:
            cursor = FeedCursor(source_id=source.id)
            session.add(cursor)

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

        health_changed = (
            outcome.status == "delayed" and before_status != "delayed"
        ) or (before_status == "delayed" and outcome.status != "delayed")
        if health_changed:
            record(
                session, "feed.health_changed", "source", source.id,
                before={"status": before_status},
                after={"status": outcome.status, "error_category": outcome.error_category},
            )

    items = (
        NormalizedIntakeItem(
            platform="rss", native_id=item.native_id, headline=item.headline,
            url=item.url, text=item.headline, published_at=item.published_at,
            edited_at=None, collected_at=item.collected_at,
            fingerprint=item.fingerprint, raw_digest=item.raw_digest,
        )
        for item in outcome.items
    )
    quarantined = (
        QuarantinedIntakeItem(
            platform="rss", reason=item.reason, raw_digest=item.raw_digest,
            native_id=item.native_id, headline=item.headline,
        )
        for item in outcome.quarantined
    )
    return store_intake_batch(db, source, items, quarantined, update_cursor, now)
