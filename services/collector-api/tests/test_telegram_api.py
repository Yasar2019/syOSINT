from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import syosint.api as api_module
from syosint.api import create_app
from syosint.models import Source
from syosint.telegram_types import ResolvedPublicChannel

from test_telegram_collect import FakeTransport, message


@pytest.fixture
def api(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SYOSINT_RSS_SCHEDULER", "0")
    monkeypatch.setenv("SYOSINT_TELEGRAM_SCHEDULER", "0")
    app = create_app(f"sqlite:///{tmp_path / 'private.sqlite'}", tmp_path / "export")
    transport = FakeTransport([message(1)])
    app.state.telegram_transport_factory = lambda: transport
    return TestClient(app, base_url="http://127.0.0.1:8765"), app, transport


def test_unconfigured_channels_are_not_resolved_or_collected(api, monkeypatch):
    client, app, transport = api
    monkeypatch.delenv("SYOSINT_TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("SYOSINT_TELEGRAM_API_HASH", raising=False)
    assert client.get("/telegram/status").json()["state"] == "not-configured"
    assert client.post("/telegram/channels/resolve", json={"username": "publicnews"}).status_code == 503
    assert transport.requests == []


def test_resolution_does_not_start_collection_and_approval_is_explicit(api, monkeypatch):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")
    resolved = client.post("/telegram/channels/resolve", json={"username": "publicnews"})
    assert resolved.status_code == 200
    assert resolved.json() == {"channel_id": 42, "username": "publicnews", "title": "Public News"}
    assert client.get("/telegram/channels").json() == []
    assert client.get("/intake-items").json() == []

    payload = {**resolved.json(), "language": "mixed"}
    created = client.post("/telegram/channels", json=payload)
    assert created.status_code == 201
    assert created.json()["username"] == "publicnews"
    assert created.json()["language"] == "mixed"
    assert client.get("/telegram/channels").json()[0]["enabled"] is True
    assert client.post("/telegram/channels", json=payload).status_code == 409
    assert client.get("/intake-items").json() == []

    synced = client.post(f"/telegram/channels/{created.json()['id']}/sync")
    assert synced.status_code == 200
    assert synced.json()["created"] == 1
    assert client.get("/intake-items").json()[0]["platform"] == "telegram"
    assert client.get("/feed-items").json() == []


def test_approval_rejects_stale_identity_and_invalid_language(api, monkeypatch):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")
    payload = {"username": "publicnews", "channel_id": 999, "title": "Spoofed", "language": "en"}
    assert client.post("/telegram/channels", json=payload).status_code == 409
    assert client.post("/telegram/channels", json={**payload, "language": "other"}).status_code == 422
    assert client.get("/telegram/channels").json() == []


def test_private_channels_cannot_be_resolved_or_approved(api, monkeypatch):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")
    transport.entity = ResolvedPublicChannel(42, "publicnews", "Private", False)
    assert client.post("/telegram/channels/resolve", json={"username": "publicnews"}).status_code == 422
    assert client.post("/telegram/channels", json={"username": "publicnews", "channel_id": 42,
                                                    "title": "Private", "language": "ar"}).status_code == 422
    assert client.get("/telegram/channels").json() == []


def test_scheduler_starts_only_with_credentials_and_approved_source(api, monkeypatch, tmp_path):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_SCHEDULER", "1")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")
    events = []

    class StubScheduler:
        def __init__(self, *args, **kwargs):
            events.append("constructed")

        def start(self):
            events.append("started")

        async def stop(self):
            events.append("stopped")

    monkeypatch.setattr(api_module, "TelegramScheduler", StubScheduler, raising=False)
    with client:
        assert "constructed" not in events
    with Session(app.state.engine) as db:
        db.add(Source(name="Public News", url="https://t.me/publicnews", kind="telegram",
                      public_identifier="publicnews", language="en", enabled=True))
        db.commit()
    second = create_app(str(app.state.engine.url), tmp_path / "export2")
    with TestClient(second, base_url="http://127.0.0.1:8765"):
        assert events == ["constructed", "started"]
    assert events == ["constructed", "started", "stopped"]


def test_transport_failure_is_redacted_in_analyst_api(api, monkeypatch):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")
    transport.failure = RuntimeError("synthetic-private-phone-and-session")
    response = client.post("/telegram/channels/resolve", json={"username": "publicnews"})
    assert response.status_code == 503
    assert "synthetic-private" not in response.text


def test_status_checks_live_authorization_without_identity_details(api, monkeypatch):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")

    async def authorized():
        return True

    transport.is_authorized = authorized
    assert client.get("/telegram/status").json() == {"state": "authenticated"}


def test_media_policy_is_off_until_analyst_enables_it(api, monkeypatch):
    client, app, transport = api
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_ID", "12345")
    monkeypatch.setenv("SYOSINT_TELEGRAM_API_HASH", "synthetic-secret")
    source_id = client.post("/telegram/channels", json={
        "username": "publicnews", "channel_id": 42, "title": "Public News", "language": "en",
    }).json()["id"]
    assert client.get("/telegram/channels").json()[0]["media_enabled"] is False
    response = client.put(f"/telegram/channels/{source_id}/media-policy", json={"enabled": True})
    assert response.status_code == 200
    assert client.get("/telegram/channels").json()[0]["media_enabled"] is True
    assert client.put(f"/telegram/channels/{source_id}/media-policy", json={"enabled": False}).status_code == 200
    assert client.get("/telegram/channels").json()[0]["media_enabled"] is False
