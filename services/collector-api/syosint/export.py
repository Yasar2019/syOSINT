import json
import os
import tempfile
from datetime import timezone
from pathlib import Path

from fastapi import HTTPException
from jsonschema import Draft202012Validator, FormatChecker
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Evidence, Incident, Source

SCHEMA = Path(__file__).resolve().parents[3] / "packages/schemas/src/public-incident.schema.json"


def build_public_record(db: Session, incident: Incident) -> dict:
    fields = incident.fields
    review = incident.review or {}
    if incident.state != "approved" or not review.get("human_approved"):
        raise HTTPException(409, "Incident requires human approval")
    required = ("title_en", "title_ar", "summary_en", "summary_ar", "uncertainty_en", "uncertainty_ar", "location_en", "location_ar", "occurred_at", "confidence")
    if any(not str(fields.get(key, "")).strip() for key in required) or not review.get("rationale"):
        raise HTTPException(409, "Bilingual text, time, confidence and rationale required")
    if not all(review.get(key) for key in ("independence_checked", "time_checked", "location_checked", "contradictions_checked", "person_safety_checked", "operational_safety_checked", "contradictions_acknowledged")):
        raise HTTPException(409, "Safety and verification checklist incomplete")
    if fields.get("precision") not in ("country", "governorate", "district", "withheld"):
        raise HTTPException(409, "Public location precision missing")
    if fields.get("precision") in ("country", "withheld") and ("latitude" in fields or "longitude" in fields):
        raise HTTPException(409, "Coordinates forbidden for country or withheld precision")
    if ("latitude" in fields) != ("longitude" in fields):
        raise HTTPException(409, "Coordinate pair incomplete")
    evidence = db.scalars(select(Evidence).where(Evidence.incident_id == incident.id).order_by(Evidence.id)).all()
    if not evidence:
        raise HTTPException(409, "At least one public source reference required")
    sources = []
    for item in evidence:
        source = db.get(Source, item.source_id)
        if source is None:
            raise HTTPException(409, "Source reference unavailable")
        sources.append({"id": str(item.id), "label": {"en": source.name, "ar": source.name}, "url": item.url, "publishedAt": item.published_at})
    location = {"en": fields["location_en"], "ar": fields["location_ar"], "precision": fields["precision"]}
    if "latitude" in fields:
        location.update(latitude=fields["latitude"], longitude=fields["longitude"])
    record = {
        "id": f"incident-{incident.id}", "status": "published", "categories": [fields["category"]],
        "confidence": fields["confidence"], "occurredAt": fields["occurred_at"],
        "updatedAt": incident.updated_at.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
        "location": location, "title": {"en": fields["title_en"], "ar": fields["title_ar"]},
        "summary": {"en": fields["summary_en"], "ar": fields["summary_ar"]},
        "uncertainty": {"en": fields["uncertainty_en"], "ar": fields["uncertainty_ar"]},
        "sourceCount": len(sources), "sources": sources, "corrections": [],
    }
    schema = json.loads(SCHEMA.read_text())
    dataset = {"schemaVersion": "1.0.0", "generatedAt": record["updatedAt"], "synthetic": False, "incidents": [record]}
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(dataset))
    if errors:
        raise HTTPException(409, "Public schema validation failed: " + errors[0].message)
    return record


def write_export(directory: Path, record: dict) -> Path:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    dataset = {"schemaVersion": "1.0.0", "generatedAt": record["updatedAt"], "synthetic": False, "incidents": [record]}
    descriptor, temporary = tempfile.mkstemp(prefix=".staging-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(dataset, output, ensure_ascii=False, indent=2)
            output.flush()
            os.fsync(output.fileno())
        path = directory / f"{record['id']}.json"
        os.replace(temporary, path)
        return path
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
