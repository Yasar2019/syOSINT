from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import syosint.api as api_module
from syosint.api import create_app
from syosint.db import database
from syosint.models import Evidence, FeedItem, Incident, Source
from syosint.rss_collect import SourceOutcome
from syosint.rss_types import NormalizedFeedItem
from syosint.safe_http import HttpValidators


NOW = datetime(2026, 9, 23, 16, 0, tzinfo=UTC)


@pytest.fixture
def api(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SYOSINT_RSS_SCHEDULER", "0")
    url = f"sqlite:///{tmp_path / 'vault.sqlite'}"
    app = create_app(url, tmp_path / "exports")
    return TestClient(app, base_url="http://127.0.0.1:8765"), url


def seed_item(url, *, incident_state=None):
    engine = database(url)
    with Session(engine) as db:
        source = db.scalar(select(Source).limit(1))
        if source is None:
            source = Source(
                name="Example feed",
                url="https://example.org/",
                language="en",
                kind="rss",
                feed_url="https://example.org/rss.xml",
            )
            db.add(source)
            db.flush()
        item_number = len(db.scalars(select(FeedItem)).all()) + 1
        incident = None
        if incident_state:
            incident = Incident(
                fields={
                    "title_en": "Existing",
                    "title_ar": "حادثة موجودة",
                    "category": "political-security",
                },
                state=incident_state,
            )
            db.add(incident)
            db.flush()
        item = FeedItem(
            source_id=source.id,
            fingerprint=f"feed-fingerprint-{item_number}",
            native_id=f"native-{item_number}",
            headline="Syria source headline",
            url=f"https://example.org/report-{item_number}",
            text="Private collected source text",
            published_at=NOW,
            collected_at=NOW,
            raw_digest="a" * 64,
            status="new",
        )
        db.add(item)
        db.commit()
        return item.id, incident.id if incident else None


def test_registers_and_lists_strict_feed_sources(api):
    client, _ = api
    payload = {
        "name": "Example RSS",
        "url": "https://example.org/",
        "feed_url": "https://example.org/rss.xml",
        "language": "en",
        "enabled": True,
        "poll_interval_minutes": 30,
    }

    created = client.post("/feeds", json=payload)

    assert created.status_code == 201
    assert client.get("/feeds").json()[0] == {
        "id": created.json()["id"],
        **payload,
        "health": {
            "status": "pending",
            "last_success_at": None,
            "consecutive_failures": 0,
            "last_error_category": None,
        },
    }
    assert client.post("/feeds", json={**payload, "extra": "no"}).status_code == 422
    assert client.post(
        "/feeds", json={**payload, "poll_interval_minutes": 5}
    ).status_code == 422
    assert client.post(
        "/feeds", json={**payload, "feed_url": "http://example.org/rss"}
    ).status_code == 422


def test_manual_collection_creates_filterable_private_inbox(api, monkeypatch):
    client, _ = api
    item = NormalizedFeedItem(
        source_id="1",
        native_id="native-1",
        headline="Fresh Syria report",
        url="https://example.org/report",
        published_at=NOW,
        collected_at=NOW,
        fingerprint="fresh-fingerprint",
        raw_digest="b" * 64,
    )

    def collect(source, now, validators):
        return SourceOutcome(
            str(source.id),
            "healthy",
            (item,),
            None,
            HttpValidators(etag='"v1"'),
        )

    monkeypatch.setattr(api_module, "default_collector", collect, raising=False)
    source_id = client.post(
        "/feeds",
        json={
            "name": "Example RSS",
            "url": "https://example.org/",
            "feed_url": "https://example.org/rss.xml",
            "language": "en",
            "enabled": True,
            "poll_interval_minutes": 30,
        },
    ).json()["id"]

    collected = client.post(f"/feeds/{source_id}/collect")

    assert collected.status_code == 200
    assert collected.json()["created"] == 1
    inbox = client.get("/feed-items", params={"status": "new"}).json()
    assert inbox[0]["headline"] == "Fresh Syria report"
    assert inbox[0]["text"] == "Fresh Syria report"
    assert client.get("/feed-items", params={"status": "invalid"}).status_code == 422


def test_promote_creates_triage_case_and_evidence_once(api):
    client, url = api
    item_id, _ = seed_item(url)
    payload = {
        "title_en": "Analyst English title",
        "title_ar": "عنوان المحلل بالعربية",
        "category": "political-security",
    }

    first = client.post(f"/feed-items/{item_id}/promote", json=payload)
    second = client.post(f"/feed-items/{item_id}/promote", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["incident_id"] == first.json()["incident_id"]
    incident_id = first.json()["incident_id"]
    assert client.get(f"/incidents/{incident_id}").json()["state"] == "triage"
    assert len(client.get(f"/incidents/{incident_id}/evidence").json()) == 1
    engine = database(url)
    with Session(engine) as db:
        evidence = db.scalar(select(Evidence).where(Evidence.incident_id == incident_id))
        assert evidence.text == "Private collected source text"
        assert evidence.digest == sha256(evidence.text.encode()).hexdigest()


def test_attach_rejects_approved_and_is_idempotent_for_open_incident(api):
    client, url = api
    locked_item, approved_id = seed_item(url, incident_state="approved")
    assert client.post(
        f"/feed-items/{locked_item}/attach", json={"incident_id": approved_id}
    ).status_code == 409

    second_item, open_id = seed_item(url, incident_state="triage")
    first = client.post(
        f"/feed-items/{second_item}/attach", json={"incident_id": open_id}
    )
    repeated = client.post(
        f"/feed-items/{second_item}/attach", json={"incident_id": open_id}
    )
    assert first.status_code == 200
    assert repeated.status_code == 200
    assert len(client.get(f"/incidents/{open_id}/evidence").json()) == 1
