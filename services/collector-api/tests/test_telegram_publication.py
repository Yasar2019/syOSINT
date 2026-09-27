from datetime import UTC, timedelta
import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from syosint.db import database
from syosint.models import IntakeItem, Source, TelegramCursor, TelegramPublication, now
from syosint.telegram_publication import (
    PublicationConflict, PublicationPayload, approve_publication, build_publication_preview,
)


def approval_payload(**changes):
    values = {
        "headline_en": "Human-written update",
        "headline_ar": "تحديث كتبه محلل",
        "source_identity_checked": True,
        "person_safety_checked": True,
        "operational_safety_checked": True,
        "human_approved": True,
    }
    return PublicationPayload(**{**values, **changes})


@pytest.fixture
def db(tmp_path: Path):
    engine = database(f"sqlite:///{tmp_path / 'private.sqlite3'}")
    with Session(engine) as session:
        source = Source(name="Public Example", url="https://t.me/publicnews",
                        kind="telegram", public_identifier="publicnews",
                        language="mixed", enabled=True)
        session.add(source)
        session.flush()
        session.add(TelegramCursor(source_id=source.id, channel_id=42))
        item = IntakeItem(
            source_id=source.id, platform="telegram", fingerprint="a" * 64,
            native_id="7", headline=None, url="https://t.me/publicnews/7",
            text="PRIVATE POST AND MEDIA DETAILS", published_at=now() - timedelta(hours=1),
            collected_at=now(), raw_digest="b" * 64, status="new",
        )
        session.add(item)
        session.commit()
        yield session, item.id, source.id


def test_preview_is_only_sanitized_and_approval_is_idempotent(db):
    session, item_id, _ = db
    draft = build_publication_preview(session, item_id, approval_payload())
    assert set(draft.record) == {
        "id", "status", "channel", "url", "headline", "publishedAt", "approvedAt", "revisions",
    }
    assert draft.record["id"] == "telegram:42:7"
    assert "PRIVATE POST" not in json.dumps(draft.record)
    publication = approve_publication(session, draft.draft_hash, approval_payload())
    assert publication.public_id == "telegram:42:7"
    assert approve_publication(session, draft.draft_hash, approval_payload()).id == publication.id
    assert "PRIVATE POST" not in json.dumps(publication.record)
    with pytest.raises(PublicationConflict, match="source changed"):
        approve_publication(session, draft.draft_hash,
                            approval_payload(headline_en="Different analyst claim"))


def test_source_edit_invalidates_exact_preview(db):
    session, item_id, _ = db
    draft = build_publication_preview(session, item_id, approval_payload())
    item = session.get(IntakeItem, item_id)
    item.raw_digest = "f" * 64
    session.commit()
    with pytest.raises(PublicationConflict, match="source changed"):
        approve_publication(session, draft.draft_hash, approval_payload())
    assert session.query(TelegramPublication).count() == 0


def test_deleted_or_misattributed_source_blocks_publication(db):
    session, item_id, source_id = db
    draft = build_publication_preview(session, item_id, approval_payload())
    item = session.get(IntakeItem, item_id)
    item.deleted_at = now()
    session.commit()
    with pytest.raises(PublicationConflict, match="deleted"):
        approve_publication(session, draft.draft_hash, approval_payload())
    item.deleted_at = None
    item.url = "https://t.me/attacker/7"
    session.commit()
    with pytest.raises(PublicationConflict, match="link changed"):
        build_publication_preview(session, item_id, approval_payload())
    item.url = "https://t.me/publicnews/7"
    source = session.get(Source, source_id)
    source.kind = "manual"
    session.commit()
    with pytest.raises(PublicationConflict, match="approved public channel"):
        build_publication_preview(session, item_id, approval_payload())


def test_all_checks_and_human_headlines_are_required(db):
    session, item_id, _ = db
    for payload in (
        approval_payload(human_approved=False),
        approval_payload(person_safety_checked=False),
        approval_payload(headline_ar="  "),
    ):
        with pytest.raises(PublicationConflict):
            build_publication_preview(session, item_id, payload)


def test_preview_expiration_requires_fresh_review(db):
    session, item_id, _ = db
    draft = build_publication_preview(session, item_id, approval_payload())
    from syosint.models import TelegramPublicationPreview
    pending = session.query(TelegramPublicationPreview).filter_by(draft_hash=draft.draft_hash).one()
    pending.expires_at = now() - timedelta(minutes=1)
    session.commit()
    with pytest.raises(PublicationConflict, match="expired"):
        approve_publication(session, draft.draft_hash, approval_payload())
