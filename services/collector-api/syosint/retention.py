"""Bounded private retention. No private strings enter run reports or audit payloads.

File unlink precedes database commit: a failed commit leaves a missing file which
is safely audited as already absent on retry. This is not secure erasure.
"""
import os
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, text, exists, and_, or_
from sqlalchemy.orm import Session

from .db import record, digest
from .models import (RetentionHold, RetentionRun, IntakeItem, IntakeRevision,
                     IntakeQuarantine, MediaAsset, Evidence, TelegramPublication,
                     TelegramPublicationPreview)

LIMIT = 1000
TARGETS = {'intake': IntakeItem, 'media': MediaAsset, 'quarantine': IntakeQuarantine}


class RetentionError(ValueError):
    pass


class RetentionConflict(RetentionError):
    pass


def utc(value):
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def clock(value):
    if value.tzinfo is None or value.utcoffset() is None:
        raise RetentionError('invalid retention time')
    return value.astimezone(UTC)


def hold_response(hold):
    result = {key: getattr(hold, key) for key in ('id', 'target_kind', 'target_id', 'reason', 'created_at', 'released_at')}
    for key in ('created_at', 'released_at'):
        if result[key] is not None: result[key] = utc(result[key])
    return result


def reason_value(reason):
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 1000:
        raise RetentionError('invalid retention request')
    return reason.strip()


def place_hold(engine, kind, target_id, reason, now):
    reason = reason_value(reason); now = clock(now)
    if kind not in TARGETS or type(target_id) is not int or target_id <= 0:
        raise RetentionError('invalid retention request')
    with Session(engine) as db:
        db.execute(text('BEGIN IMMEDIATE'))
        if db.get(TARGETS[kind], target_id) is None:
            raise RetentionError('retention target unavailable')
        hold = db.scalar(select(RetentionHold).where(RetentionHold.target_kind == kind, RetentionHold.target_id == target_id, RetentionHold.released_at.is_(None)))
        if hold is not None and hold.released_at is None:
            raise RetentionConflict('retention hold conflict')
        if hold is None:
            hold = RetentionHold(target_kind=kind, target_id=target_id)
            db.add(hold)
        hold.reason = reason; hold.created_at = now; hold.released_at = None
        db.flush()
        record(db, 'retention.hold', 'retention_hold', hold.id, after={'kind': kind, 'id': target_id, 'reason_hash': digest(reason)})
        result = hold_response(hold); db.commit(); return result


def release_hold(engine, hold_id, reason, now):
    reason = reason_value(reason); now = clock(now)
    if type(hold_id) is not int or hold_id <= 0:
        raise RetentionError('invalid retention request')
    with Session(engine) as db:
        db.execute(text('BEGIN IMMEDIATE'))
        hold = db.get(RetentionHold, hold_id)
        if hold is None:
            raise RetentionError('retention target unavailable')
        if hold.released_at is not None:
            raise RetentionConflict('retention hold conflict')
        hold.released_at = now
        record(db, 'retention.release', 'retention_hold', hold.id, after={'released': True, 'reason_hash': digest(reason)})
        result = hold_response(hold); db.commit(); return result


def safe_file(path_value, root_value, *, unlink=False):
    """Walk every absolute ancestor with O_NOFOLLOW; unlink using retained dirfd."""
    path = Path(path_value); root = Path(root_value)
    if (not path.is_absolute() or not root.is_absolute() or '..' in path.parts or
            '..' in root.parts or path.suffix != '.bin' or not path.is_relative_to(root) or path == root):
        raise RetentionError('unsafe media')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for component in path.parent.parts[1:]:
            try:
                child = os.open(component, flags, dir_fd=fd)
            except FileNotFoundError:
                return False
            os.close(fd); fd = child
        try:
            info = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise RetentionError('unsafe media')
        if unlink:
            # Recheck identity immediately before unlink; ancestor replacement cannot redirect fd.
            checked = os.stat(path.name, dir_fd=fd, follow_symlinks=False)
            if (checked.st_dev, checked.st_ino, checked.st_nlink, checked.st_mode) != (info.st_dev, info.st_ino, info.st_nlink, info.st_mode):
                raise RetentionError('unsafe media')
            os.unlink(path.name, dir_fd=fd)
        return True
    finally:
        os.close(fd)


def run_retention(engine, media_root, now, *, apply=False, media_only=False):
    now = clock(now)
    counts = dict.fromkeys(('media', 'intake', 'quarantine', 'previews', 'protected', 'failed', 'bounded'), 0)
    with Session(engine) as db:
        if apply:
            db.execute(text('BEGIN IMMEDIATE'))
        def protected(item):
            return db.scalar(select(IntakeItem.id).where(IntakeItem.id == item.id, item_protected).limit(1)) is not None
        def batch(model, *conditions):
            rows = list(db.scalars(select(model).where(*conditions).order_by(model.id).limit(LIMIT+1)))
            counts['bounded'] += int(len(rows)>LIMIT)
            return rows[:LIMIT]
        def remove(row, entity):
            record(db,'retention.deleted',entity,row.id,before={'id':row.id},after={'deleted':True})
            db.delete(row)
        # Filter relational protections before LIMIT so a held prefix cannot starve
        # eligible records on every repeated bounded run.
        hold_item = exists(select(RetentionHold.id).where(RetentionHold.target_kind == 'intake', RetentionHold.target_id == IntakeItem.id, RetentionHold.released_at.is_(None)))
        hold_child = exists(select(MediaAsset.id).join(RetentionHold, and_(RetentionHold.target_kind == 'media', RetentionHold.target_id == MediaAsset.id, RetentionHold.released_at.is_(None))).where(MediaAsset.item_id == IntakeItem.id))
        item_protected = or_(IntakeItem.incident_id.is_not(None), IntakeItem.status == 'promoted', hold_item, hold_child,
            exists(select(Evidence.id).where(Evidence.source_id == IntakeItem.source_id, Evidence.url == IntakeItem.url)),
            exists(select(TelegramPublication.id).where(TelegramPublication.item_id == IntakeItem.id)),
            exists(select(TelegramPublicationPreview.id).where(TelegramPublicationPreview.item_id == IntakeItem.id, TelegramPublicationPreview.expires_at > now)))
        protected_ids = select(IntakeItem.id).where(item_protected)
        media_expired = or_(MediaAsset.expires_at <= now, MediaAsset.collected_at <= now-timedelta(days=30))
        counts['protected'] += len(list(db.scalars(select(MediaAsset.id).where(MediaAsset.deleted_at.is_(None), media_expired, MediaAsset.item_id.in_(protected_ids)).limit(LIMIT))))
        expired = batch(MediaAsset, MediaAsset.deleted_at.is_(None), media_expired, MediaAsset.item_id.not_in(protected_ids))
        completed = set()
        for asset in expired:
            item = db.get(IntakeItem,asset.item_id)
            if item is None or protected(item):
                counts['protected'] += 1; continue
            try:
                existed = safe_file(asset.local_path,media_root,unlink=apply)
            except (OSError, RetentionError):
                counts['failed'] += 1; continue
            counts['media'] += 1; completed.add(asset.id)
            if apply:
                asset.deleted_at = now
                record(db,'media.deleted','media_asset',asset.id,before={'sha256':asset.sha256},after={'deleted':True,'already_absent':not existed})
        if not media_only:
            expired_previews = batch(TelegramPublicationPreview, TelegramPublicationPreview.expires_at <= now)
            preview_ids = {p.id for p in expired_previews}
            for preview in expired_previews:
                counts['previews'] += 1
                if apply: remove(preview,'telegram_publication_preview')
            db.flush()
            metadata_old = IntakeItem.collected_at < now-timedelta(days=180)
            counts['protected'] += len(list(db.scalars(select(IntakeItem.id).where(metadata_old, item_protected).limit(LIMIT))))
            recent_revision = exists(select(IntakeRevision.id).where(IntakeRevision.item_id == IntakeItem.id, IntakeRevision.collected_at >= now-timedelta(days=180)))
            live_media = exists(select(MediaAsset.id).where(MediaAsset.item_id == IntakeItem.id, MediaAsset.deleted_at.is_(None), MediaAsset.id.not_in(completed)))
            revision_budget = asset_budget = LIMIT
            for item in batch(IntakeItem, metadata_old, ~item_protected, ~recent_revision, ~live_media):
                if protected(item):
                    counts['protected'] += 1; continue
                revisions = list(db.scalars(select(IntakeRevision).where(IntakeRevision.item_id == item.id).order_by(IntakeRevision.id).limit(revision_budget + 1)))
                if any(utc(r.collected_at) >= now-timedelta(days=180) for r in revisions):
                    continue
                assets = list(db.scalars(select(MediaAsset).where(MediaAsset.item_id == item.id).order_by(MediaAsset.id).limit(asset_budget + 1)))
                if any(a.deleted_at is None and a.id not in completed for a in assets):
                    counts['protected'] += 1; continue
                # Children beyond a bounded preview batch keep the parent for a later run.
                remaining = db.scalar(select(TelegramPublicationPreview.id).where(TelegramPublicationPreview.item_id == item.id, TelegramPublicationPreview.id.not_in(preview_ids)).limit(1))
                if remaining is not None:
                    continue
                remaining_children = len(revisions) > revision_budget or len(assets) > asset_budget
                selected_revisions = revisions[:revision_budget]
                selected_assets = assets[:asset_budget]
                revision_budget -= len(selected_revisions)
                asset_budget -= len(selected_assets)
                if apply:
                    for row in selected_revisions + selected_assets: remove(row,row.__tablename__)
                if remaining_children:
                    counts['bounded'] += 1
                    continue
                counts['intake'] += 1
                if apply:
                    remove(item,'intake_item')
            quarantine_held = exists(select(RetentionHold.id).where(RetentionHold.target_kind == 'quarantine', RetentionHold.target_id == IntakeQuarantine.id, RetentionHold.released_at.is_(None)))
            counts['protected'] += len(list(db.scalars(select(IntakeQuarantine.id).where(IntakeQuarantine.created_at < now-timedelta(days=180), quarantine_held).limit(LIMIT))))
            for row in batch(IntakeQuarantine, IntakeQuarantine.created_at < now-timedelta(days=180), ~quarantine_held):
                counts['quarantine'] += 1
                if apply: remove(row,'intake_quarantine')
        counts['bounded'] = bool(counts['bounded'])
        if apply:
            db.add(RetentionRun(timestamp=now,dry_run=False,counts=counts,status='partial' if counts['failed'] or counts['bounded'] else 'complete'))
            db.commit()
    return counts
