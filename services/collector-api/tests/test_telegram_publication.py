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


def test_expired_source_post_cannot_be_approved_into_an_invisible_public_wire(db):
    session, item_id, _ = db
    item = session.get(IntakeItem, item_id)
    item.published_at = now() - timedelta(days=8)
    session.commit()
    with pytest.raises(PublicationConflict, match="seven-day publication window"):
        build_publication_preview(session, item_id, approval_payload())


def test_approval_rechecks_capacity_after_two_previews_compete_for_one_slot(db, monkeypatch):
    import syosint.telegram_publication as publication_service
    monkeypatch.setattr(publication_service, "MAX_PUBLIC_TELEGRAM_ENTRIES", 1)
    session, item_id, source_id = db
    second = IntakeItem(
        source_id=source_id, platform="telegram", fingerprint="c" * 64,
        native_id="8", headline=None, url="https://t.me/publicnews/8",
        text="OTHER PRIVATE POST", published_at=now() - timedelta(hours=1),
        collected_at=now(), raw_digest="d" * 64, status="new",
    )
    session.add(second)
    session.commit()
    first_preview = build_publication_preview(session, item_id, approval_payload())
    second_preview = build_publication_preview(session, second.id, approval_payload())
    approve_publication(session, first_preview.draft_hash, approval_payload())
    with pytest.raises(PublicationConflict, match="capacity"):
        approve_publication(session, second_preview.draft_hash, approval_payload())
    assert session.query(TelegramPublication).count() == 1


def test_preview_expiration_requires_fresh_review(db):
    session, item_id, _ = db
    draft = build_publication_preview(session, item_id, approval_payload())
    from syosint.models import TelegramPublicationPreview
    pending = session.query(TelegramPublicationPreview).filter_by(draft_hash=draft.draft_hash).one()
    pending.expires_at = now() - timedelta(minutes=1)
    session.commit()
    with pytest.raises(PublicationConflict, match="expired"):
        approve_publication(session, draft.draft_hash, approval_payload())


def test_correction_and_withdrawal_append_explicit_history(db):
    from syosint.models import TelegramPublicationRevision
    from syosint.telegram_publication import correct_publication, withdraw_publication, publication_attention
    session, item_id, _ = db
    draft = build_publication_preview(session, item_id, approval_payload())
    publication = approve_publication(session, draft.draft_hash, approval_payload())
    item = session.get(IntakeItem, item_id)
    item.raw_digest = "c" * 64
    session.commit()
    assert publication_attention(session) == [
        {"id": publication.id, "item_id": item_id, "public_id": "telegram:42:7", "reason": "source-edited"}
    ]
    corrected = correct_publication(
        session, publication.id, approval_payload(headline_en="Corrected analyst headline"),
        "Corrected attribution", "تصحيح النسبة")
    assert corrected.status == "corrected"
    assert corrected.record["revisions"][0]["previousHeadline"]["en"] == "Human-written update"
    assert publication_attention(session) == []
    item.deleted_at = now()
    session.commit()
    assert publication_attention(session)[0]["reason"] == "source-deleted"
    with pytest.raises(PublicationConflict, match="explicit"):
        withdraw_publication(session, publication.id, "Source withdrew", "سحب المصدر", False)
    withdrawn = withdraw_publication(session, publication.id, "Source withdrew", "سحب المصدر", True)
    assert withdrawn.status == "withdrawn"
    assert withdrawn.record["revisions"][-1]["action"] == "withdrawn"
    assert len(withdrawn.record["revisions"]) == 2
    assert publication_attention(session) == []
    assert session.query(TelegramPublicationRevision).count() == 2
