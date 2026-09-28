import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from syosint.api import create_app
from syosint.models import IntakeItem, Source, TelegramCursor, now
from syosint.telegram_export import stage_telegram_wire


@pytest.fixture
def local(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SYOSINT_RSS_SCHEDULER", "0")
    monkeypatch.setenv("SYOSINT_TELEGRAM_SCHEDULER", "0")
    app = create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / "pending-exports")
    with Session(app.state.engine) as db:
        source = Source(name="Synthetic Public Channel", url="https://t.me/publicnews",
                        kind="telegram", public_identifier="publicnews",
                        language="en", enabled=True)
        db.add(source)
        db.flush()
        db.add(TelegramCursor(source_id=source.id, channel_id=42))
        post = IntakeItem(
            source_id=source.id, platform="telegram", fingerprint="a" * 64,
            native_id="7", headline=None, url="https://t.me/publicnews/7",
            text="PRIVATE SYNTHETIC POST", published_at=now() - timedelta(hours=1),
            collected_at=now(), raw_digest="b" * 64, status="new",
        )
        db.add(post)
        db.commit()
        item_id = post.id
    return TestClient(app, base_url="http://127.0.0.1:8765"), app, item_id, tmp_path


def payload(**changes):
    return {
        "headline_en": "Human reviewed report",
        "headline_ar": "تقرير راجعه محلل",
        "source_identity_checked": True,
        "person_safety_checked": True,
        "operational_safety_checked": True,
        "human_approved": True,
        **changes,
    }


def test_preview_approve_and_manual_stage_require_individual_consent(local):
    client, app, item_id, root = local
    path = f"/intake-items/{item_id}"
    rejected = client.post(f"{path}/publication-preview", json={**payload(), "rawText": "LEAK"})
    assert rejected.status_code == 422
    preview = client.post(f"{path}/publication-preview", json=payload())
    assert preview.status_code == 200
    draft = preview.json()
    assert "PRIVATE SYNTHETIC POST" not in json.dumps(draft)
    assert set(draft["record"]) == {
        "id", "status", "channel", "url", "headline",
        "publishedAt", "approvedAt", "revisions",
    }
    assert client.post(f"{path}/publication-approve", json={
        **payload(), "draft_hash": "0" * 64,
    }).status_code == 409
    assert not (root / "pending-exports").exists()
    approved = client.post(f"{path}/publication-approve", json={
        **payload(), "draft_hash": draft["draft_hash"],
    })
    assert approved.status_code == 200
    assert approved.json()["status"] == "active"
    pending = root / "pending-exports/telegram-pending.v1.json"
    assert pending.exists()
    assert "PRIVATE SYNTHETIC POST" not in pending.read_text()
    assert client.post(f"{path}/publication-approve", json={
        **payload(), "draft_hash": draft["draft_hash"],
    }).json()["id"] == approved.json()["id"]
    tracked = root / "public.json"
    tracked.write_text(json.dumps({
        "schemaVersion": "1.0.0", "generatedAt": draft["record"]["approvedAt"],
        "lastEditorialUpdateAt": draft["record"]["approvedAt"], "entries": [],
    }))
    assert json.loads(tracked.read_text())["entries"] == []
    stage_telegram_wire(pending, tracked, tracked, now())
    assert json.loads(tracked.read_text())["entries"][0]["id"] == "telegram:42:7"


def test_source_edit_and_deletion_require_explicit_correction_and_withdrawal(local):
    client, app, item_id, root = local
    path = f"/intake-items/{item_id}"
    draft = client.post(f"{path}/publication-preview", json=payload()).json()
    with Session(app.state.engine) as db:
        post = db.get(IntakeItem, item_id)
        post.raw_digest = "c" * 64
        db.commit()
    assert client.post(f"{path}/publication-approve", json={
        **payload(), "draft_hash": draft["draft_hash"],
    }).status_code == 409
    revised = client.post(f"{path}/publication-preview", json=payload()).json()
    pub = client.post(f"{path}/publication-approve", json={
        **payload(), "draft_hash": revised["draft_hash"],
    }).json()
    with Session(app.state.engine) as db:
        post = db.get(IntakeItem, item_id)
        post.raw_digest = "d" * 64
        db.commit()
    assert client.get("/telegram-publications/attention").json()[0]["reason"] == "source-edited"
    corrected = client.post(f"/telegram-publications/{pub['id']}/correct", json={
        **payload(headline_en="Corrected reviewed headline"),
        "reason_en": "Updated attribution", "reason_ar": "تحديث النسبة",
    })
    assert corrected.status_code == 200
    assert corrected.json()["status"] == "corrected"
    with Session(app.state.engine) as db:
        db.get(IntakeItem, item_id).deleted_at = now()
        db.commit()
    assert client.get("/telegram-publications/attention").json()[0]["reason"] == "source-deleted"
    withdrawn = client.post(f"/telegram-publications/{pub['id']}/withdraw", json={
        "reason_en": "Source removed post", "reason_ar": "حذف المصدر المنشور",
        "human_approved": True,
    })
    assert withdrawn.status_code == 200
    assert client.get("/telegram-publications/attention").json() == []
    pending = json.loads((root / "pending-exports/telegram-pending.v1.json").read_text())
    assert [part["action"] for part in pending["entries"][0]["revisions"]] == [
        "corrected", "withdrawn",
    ]
    assert "PRIVATE SYNTHETIC POST" not in json.dumps(pending)
