from collections.abc import Callable, Iterable
from dataclasses import asdict
from datetime import datetime
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from .intake_types import NormalizedIntakeItem, QuarantinedIntakeItem, StoreSummary
from .models import IntakeItem, IntakeQuarantine, IntakeRevision, Source


def _store_item(db: Session, source_id: int, item: NormalizedIntakeItem) -> bool:
    """Return True for a new item; RSS retains legacy duplicate observations."""
    query = select(IntakeItem).where(IntakeItem.source_id == source_id)
    existing = None
    if item.platform == "telegram" and item.native_id is not None:
        existing = db.scalar(query.where(
            IntakeItem.native_id == item.native_id,
            IntakeItem.status != "duplicate",
        ))
    if existing is None:
        existing = db.scalar(query.where(IntakeItem.fingerprint == item.fingerprint))
    if existing is None:
        db.add(IntakeItem(source_id=source_id, status="new", **asdict(item)))
        return True

    if item.platform == "rss":
        duplicate_fingerprint = sha256(
            f"duplicate\0{item.fingerprint}\0{item.raw_digest}".encode()
        ).hexdigest()
        duplicate = db.scalar(query.where(IntakeItem.fingerprint == duplicate_fingerprint))
        if duplicate is None:
            values = asdict(item)
            values["fingerprint"] = duplicate_fingerprint
            db.add(IntakeItem(source_id=source_id, status="duplicate", **values))
    elif existing.raw_digest != item.raw_digest:
        db.add(IntakeRevision(
            item_id=existing.id, text=existing.text, raw_digest=existing.raw_digest,
            edited_at=existing.edited_at, collected_at=existing.collected_at,
        ))
        # Keep durable identity and analyst resolution; never mutate linked evidence.
        for field in ("headline", "url", "text", "published_at", "edited_at",
                      "collected_at", "raw_digest"):
            setattr(existing, field, getattr(item, field))
    return False


def store_intake_batch(
    db: Session,
    source: Source,
    items: Iterable[NormalizedIntakeItem],
    quarantined: Iterable[QuarantinedIntakeItem],
    cursor_update: Callable[[Session], None] | None,
    now: datetime,
) -> StoreSummary:
    """Commit a private batch, cursor and audit atomically on the supplied Session.

    The caller gives this function ownership of the Session's transaction. The
    optional synchronous callback may mutate cursor/audit rows on that Session
    only: it must not commit, roll back, perform network I/O or external writes.
    Items are flushed before the callback; any failure rolls back the complete
    transaction. `duplicates` counts existing deliveries, including revisions.
    """
    created = duplicates = quarantine_created = 0
    try:
        for item in items:
            if _store_item(db, source.id, item):
                created += 1
            else:
                duplicates += 1
            # Same-batch deduplication also works with autoflush disabled.
            db.flush()

        for item in quarantined:
            existing = db.scalar(select(IntakeQuarantine).where(
                IntakeQuarantine.source_id == source.id,
                IntakeQuarantine.raw_digest == item.raw_digest,
                IntakeQuarantine.reason == item.reason,
            ))
            if existing is None:
                db.add(IntakeQuarantine(source_id=source.id, created_at=now, **asdict(item)))
                quarantine_created += 1
                db.flush()

        if cursor_update is not None:
            cursor_update(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return StoreSummary(created, duplicates, quarantine_created)
