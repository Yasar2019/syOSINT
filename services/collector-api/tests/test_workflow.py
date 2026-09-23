from pathlib import Path

from fastapi.testclient import TestClient

from syosint.api import create_app


def test_source_incident_evidence_and_audit(tmp_path: Path):
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / "exports"))
    source = client.post("/sources", json={"name": "Example Gazette", "url": "https://example.org/news", "language": "en"})
    assert source.status_code == 201
    source_id = source.json()["id"]
    incident = client.post("/incidents", json={"title_en": "Power outage", "title_ar": "انقطاع الكهرباء", "category": "infrastructure"})
    assert incident.status_code == 201
    incident_id = incident.json()["id"]
    evidence = client.post(f"/incidents/{incident_id}/evidence", json={"source_id": source_id, "url": "https://example.org/news/1", "text": "Original report kept private", "published_at": "2026-09-23T10:00:00Z"})
    assert evidence.status_code == 201
    assert len(client.get(f"/incidents/{incident_id}/evidence").json()) == 1
    audit = client.get("/audit").json()
    assert [row["action"] for row in audit] == ["source.created", "incident.created", "evidence.created"]
    assert "Original report kept private" not in str(audit)


def test_rejects_private_addresses_and_unexpected_fields(tmp_path: Path):
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / "exports"))
    credential_url = "https://" + "user:" + "pass@" + "example.org/"
    for url in ("http://example.org", "https://localhost/private", "https://127.0.0.1/", credential_url, "https://example.org:bad/path"):
        assert client.post("/sources", json={"name": "Source", "url": url, "language": "en"}).status_code == 422
    assert client.post("/sources", json={"name": "Source", "url": "https://example.org", "language": "en", "secret": "abc"}).status_code == 422


def test_review_preview_and_explicit_export(tmp_path: Path):
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / "exports"))
    source_id = client.post("/sources", json={"name": "Public journal", "url": "https://example.org", "language": "en"}).json()["id"]
    incident_id = client.post("/incidents", json={"title_en": "Road closure", "title_ar": "إغلاق طريق", "category": "infrastructure"}).json()["id"]
    assert client.get(f"/incidents/{incident_id}/preview").status_code == 409
    client.post(f"/incidents/{incident_id}/evidence", json={"source_id": source_id, "url": "https://example.org/report", "text": "PRIVATE witness account", "published_at": "2026-09-23T10:00:00Z"})
    edit = {
        "title_en": "Road closure", "title_ar": "إغلاق طريق", "category": "infrastructure",
        "summary_en": "A road closure was reported.", "summary_ar": "ورد تقرير عن إغلاق طريق.",
        "uncertainty_en": "Cause not established.", "uncertainty_ar": "السبب غير مؤكد.",
        "location_en": "Syria", "location_ar": "سوريا", "precision": "country",
        "occurred_at": "2026-09-23T10:00:00Z", "confidence": "unverified",
    }
    assert client.put(f"/incidents/{incident_id}", json=edit).status_code == 200
    for state in ("investigating", "review-ready"):
        assert client.post(f"/incidents/{incident_id}/transition", json={"state": state, "reason": "Reviewed public reference"}).status_code == 200
    assert client.post(f"/incidents/{incident_id}/transition", json={"state": "approved", "reason": "Human approval"}).status_code == 409
    review = {"rationale": "One original reference, unverified.", "independence_checked": True,
              "time_checked": True, "location_checked": True, "contradictions_checked": True,
              "person_safety_checked": True, "operational_safety_checked": True,
              "contradictions_acknowledged": True, "human_approved": True}
    assert client.post(f"/incidents/{incident_id}/review", json=review).status_code == 200
    assert client.post(f"/incidents/{incident_id}/transition", json={"state": "approved", "reason": "Human approval"}).status_code == 200
    preview = client.get(f"/incidents/{incident_id}/preview")
    assert preview.status_code == 200
    assert "PRIVATE" not in str(preview.json())
    assert preview.json()["sources"][0]["url"] == "https://example.org/report"
    assert not (tmp_path / "exports").exists()
    exported = client.post(f"/incidents/{incident_id}/export", json={"acknowledged": True})
    assert exported.status_code == 200
    assert exported.json()["record"] == preview.json()
    assert len(list((tmp_path / "exports").glob("*.json"))) == 1
    assert client.get("/audit").json()[-1]["action"] == "incident.exported"
    assert client.post(f"/incidents/{incident_id}/evidence", json={"source_id": source_id, "url": "https://example.org/late", "text": "Unreviewed", "published_at": "2026-09-23T11:00:00Z"}).status_code == 409


def test_unsafe_location_and_incomplete_review_block_export(tmp_path: Path):
    client = TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / "exports"))
    incident_id = client.post("/incidents", json={"title_en": "Update", "title_ar": "تحديث", "category": "political-security"}).json()["id"]
    assert client.post(f"/incidents/{incident_id}/review", json={"rationale": "Fine", "human_approved": True}).status_code == 422
    assert client.post(f"/incidents/{incident_id}/export", json={"acknowledged": True}).status_code == 409


def test_migration_and_records_survive_restart(tmp_path: Path):
    import sqlite3

    vault = tmp_path / "vault.sqlite"
    app_url = f"sqlite:///{vault}"
    first = TestClient(create_app(app_url, tmp_path / "exports"))
    assert first.post("/sources", json={"name": "Journal", "url": "https://example.org", "language": "en"}).status_code == 201
    with sqlite3.connect(vault) as connection:
        assert connection.execute("select version_num from alembic_version").fetchone()[0] == "0001"
    second = TestClient(create_app(app_url, tmp_path / "exports"))
    assert second.get("/sources").json()[0]["name"] == "Journal"
    assert len(second.get("/audit").json()) == 1
