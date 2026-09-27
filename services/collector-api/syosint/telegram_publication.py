"""Explicit, local editorial gate for individually reviewed public Telegram leads.

Only sanitized bilingual records and hashes are persisted here. Source text remains
in the private intake table and never enters a publication record or audit payload.
"""
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import record as audit_record
from .models import (
    IntakeItem, Source, TelegramCursor, TelegramPublication,
    TelegramPublicationPreview, now as current_time,
)

USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
PREVIEW_LIFETIME = timedelta(minutes=15)


class PublicationConflict(ValueError):
    pass


@dataclass(frozen=True)
class PublicationPayload:
    headline_en: str
    headline_ar: str
    source_identity_checked: bool
    person_safety_checked: bool
    operational_safety_checked: bool
    human_approved: bool


@dataclass(frozen=True)
class PublicationDraft:
    draft_hash: str
    record: dict


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _stamp(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _sanitized_record(db: Session, item_id: int, payload: PublicationPayload,
                      at: datetime) -> tuple[dict, str]:
    if not all((
        payload.source_identity_checked, payload.person_safety_checked,
        payload.operational_safety_checked, payload.human_approved,
    )):
        raise PublicationConflict("all human safety checks are required")
    headlines = (payload.headline_en.strip(), payload.headline_ar.strip())
    if any(not text or len(text) < 3 or len(text) > 240 for text in headlines):
        raise PublicationConflict("two human-written public headlines are required")
    item = db.get(IntakeItem, item_id)
    if item is None or item.platform != "telegram" or item.status not in ("new", "promoted", "attached"):
        raise PublicationConflict("approved public Telegram item required")
    if item.deleted_at is not None:
        raise PublicationConflict("source post was deleted")
    source = db.get(Source, item.source_id)
    cursor = db.get(TelegramCursor, item.source_id)
    if (source is None or source.kind != "telegram" or not source.enabled or cursor is None
            or cursor.channel_id is None or cursor.channel_id <= 0):
        raise PublicationConflict("approved public channel required")
    username = source.public_identifier or ""
    native_id = item.native_id or ""
    if (not USERNAME.fullmatch(username) or not native_id.isascii() or not native_id.isdecimal()
            or int(native_id) <= 0 or source.language not in ("en", "ar", "mixed")
            or item.url != f"https://t.me/{username}/{native_id}"):
        raise PublicationConflict("source identity or permanent public link changed")
    if not source.name.strip() or len(source.name) > 250 or not HASH.fullmatch(item.raw_digest):
        raise PublicationConflict("source identity or source digest invalid")
    if _utc(item.published_at) > _utc(at):
        raise PublicationConflict("source publication time is invalid")
    sanitized = {
        "id": f"telegram:{cursor.channel_id}:{native_id}",
        "status": "active",
        "channel": {"name": source.name, "username": username, "language": source.language},
        "url": item.url,
        "headline": {"en": headlines[0], "ar": headlines[1]},
        "publishedAt": _stamp(item.published_at),
        "approvedAt": _stamp(at),
        "revisions": [],
    }
    return sanitized, item.raw_digest


def _draft_hash(item_id: int, sanitized: dict, source_digest: str) -> str:
    data = {"item_id": item_id, "record": sanitized, "digest": source_digest}
    return sha256(json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_publication_preview(db: Session, item_id: int, payload: PublicationPayload,
                              at: datetime | None = None) -> PublicationDraft:
    checked_at = _utc(at or current_time())
    if checked_at > _utc(current_time()) + timedelta(minutes=1):
        raise PublicationConflict("invalid review time")
    sanitized, source_digest = _sanitized_record(db, item_id, payload, checked_at)
    draft_hash = _draft_hash(item_id, sanitized, source_digest)
    safety = {
        "source_identity_checked": payload.source_identity_checked,
        "person_safety_checked": payload.person_safety_checked,
        "operational_safety_checked": payload.operational_safety_checked,
        "human_approved": payload.human_approved,
    }
    prior = db.scalar(select(TelegramPublicationPreview).where(
        TelegramPublicationPreview.draft_hash == draft_hash))
    if prior is None:
        db.add(TelegramPublicationPreview(
            item_id=item_id, draft_hash=draft_hash, source_digest=source_digest,
            record=sanitized, safety=safety, created_at=checked_at,
            expires_at=checked_at + PREVIEW_LIFETIME,
        ))
        db.commit()
    return PublicationDraft(draft_hash=draft_hash, record=sanitized)


def approve_publication(db: Session, draft_hash: str, payload: PublicationPayload,
                        at: datetime | None = None) -> TelegramPublication:
    if not HASH.fullmatch(draft_hash):
        raise PublicationConflict("invalid review hash")
    draft = db.scalar(select(TelegramPublicationPreview).where(
        TelegramPublicationPreview.draft_hash == draft_hash))
    if draft is None or _utc(draft.expires_at) < _utc(at or current_time()):
        raise PublicationConflict("preview expired; review again")
    checked_at = _utc(datetime.fromisoformat(draft.record["approvedAt"].replace("Z", "+00:00")))
    current_record, current_digest = _sanitized_record(db, draft.item_id, payload, checked_at)
    if (draft.source_digest != current_digest or draft.record != current_record
            or _draft_hash(draft.item_id, current_record, current_digest) != draft_hash
            or not all(draft.safety.values())):
        raise PublicationConflict("source changed; review again")
    prior = db.scalar(select(TelegramPublication).where(TelegramPublication.item_id == draft.item_id))
    if prior is not None:
        if prior.record == current_record and prior.source_digest == current_digest:
            return prior
        raise PublicationConflict("post is already approved; use editorial correction")
    published = TelegramPublication(
        item_id=draft.item_id, public_id=current_record["id"],
        source_digest=current_digest, record=current_record, status="active",
        approved_at=checked_at,
    )
    db.add(published)
    db.flush()
    audit_record(db, "telegram.publication.approved", "telegram_publication",
                 published.id, after={"public_id": published.public_id, "draft_hash": draft_hash})
    db.commit()
    return published
