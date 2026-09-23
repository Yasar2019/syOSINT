import hashlib
import ipaddress
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import database, record
from .export import build_public_record, write_export
from .models import Audit, Evidence, Incident, Source, now


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


def public_url(value: str) -> str:
    url = urlsplit(value)
    hostname = url.hostname or ""
    try:
        ipaddress.ip_address(hostname)
        raise ValueError("IP address references are not allowed")
    except ValueError as exc:
        if str(exc) == "IP address references are not allowed":
            raise
    if (url.scheme != "https" or not hostname or "." not in hostname or
            hostname.endswith((".local", ".localhost", ".internal")) or
            url.username or url.password or url.fragment or url.port not in (None, 443)):
        raise ValueError("Use a public HTTPS reference without credentials or fragments")
    return value


class SourceInput(Strict):
    name: str
    url: str
    language: str

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return public_url(value)


class IncidentInput(Strict):
    title_en: str
    title_ar: str
    category: str


class EvidenceInput(Strict):
    source_id: int
    url: str
    text: str
    published_at: str

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        return public_url(value)


class IncidentEdit(IncidentInput):
    summary_en: str
    summary_ar: str
    uncertainty_en: str
    uncertainty_ar: str
    location_en: str
    location_ar: str
    precision: str
    latitude: float | None = None
    longitude: float | None = None
    occurred_at: datetime
    confidence: str

    @field_validator("precision")
    @classmethod
    def check_precision(cls, value):
        if value not in ("country", "governorate", "district", "withheld"):
            raise ValueError("Invalid public precision")
        return value

    @field_validator("confidence")
    @classmethod
    def check_confidence(cls, value):
        if value not in ("unverified", "developing", "corroborated", "verified", "disputed", "false"):
            raise ValueError("Invalid confidence")
        return value

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        if value not in ("armed-conflict", "political-security", "humanitarian", "infrastructure", "border-crossing", "disinformation"):
            raise ValueError("Invalid category")
        return value


class ReviewInput(Strict):
    rationale: str = Field(min_length=10)
    independence_checked: bool
    time_checked: bool
    location_checked: bool
    contradictions_checked: bool
    person_safety_checked: bool
    operational_safety_checked: bool
    contradictions_acknowledged: bool
    human_approved: bool


class TransitionInput(Strict):
    state: str
    reason: str = Field(min_length=8)


class ExportInput(Strict):
    acknowledged: bool


def create_app(database_url: str, export_dir: Path) -> FastAPI:
    engine = database(database_url)
    app = FastAPI(title="syOSINT local analyst API")
    app.state.export_dir = export_dir

    def session():
        with Session(engine) as db:
            yield db

    @app.post("/sources", status_code=201)
    def add_source(item: SourceInput, db: Session = Depends(session)):
        if db.scalar(select(Source).where(Source.url == item.url)):
            raise HTTPException(409, "Source already exists")
        source = Source(**item.model_dump())
        db.add(source)
        db.flush()
        record(db, "source.created", "source", source.id, after=item.model_dump())
        db.commit()
        return {"id": source.id, **item.model_dump()}

    @app.get("/sources")
    def list_sources(db: Session = Depends(session)):
        return [{"id": s.id, "name": s.name, "url": s.url, "language": s.language} for s in db.scalars(select(Source).order_by(Source.id))]

    @app.post("/incidents", status_code=201)
    def add_incident(item: IncidentInput, db: Session = Depends(session)):
        incident = Incident(fields=item.model_dump())
        db.add(incident)
        db.flush()
        record(db, "incident.created", "incident", incident.id, after=item.model_dump())
        db.commit()
        return {"id": incident.id, "state": incident.state, **incident.fields}

    @app.get("/incidents")
    def list_incidents(db: Session = Depends(session)):
        return [{"id": i.id, "state": i.state, **i.fields} for i in db.scalars(select(Incident).order_by(Incident.id.desc()))]

    @app.get("/incidents/{incident_id}")
    def get_incident(incident_id: int, db: Session = Depends(session)):
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(404, "Incident not found")
        return {"id": incident.id, "state": incident.state, "review": incident.review, **incident.fields}

    @app.put("/incidents/{incident_id}")
    def edit_incident(incident_id: int, item: IncidentEdit, db: Session = Depends(session)):
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(404, "Incident not found")
        if incident.state in ("approved", "published", "withdrawn"):
            raise HTTPException(409, "Approved incident is locked; use a correction workflow")
        fields = item.model_dump(mode="json", exclude_none=True)
        if ("latitude" in fields) != ("longitude" in fields) or (fields["precision"] in ("country", "withheld") and "latitude" in fields):
            raise HTTPException(422, "Unsafe or incomplete public coordinates")
        before = incident.fields
        incident.fields = fields
        incident.review = {}
        incident.updated_at = now()
        record(db, "incident.edited", "incident", incident.id, before=before, after=fields)
        db.commit()
        return {"id": incident.id, "state": incident.state, **incident.fields}

    @app.post("/incidents/{incident_id}/review")
    def review_incident(incident_id: int, item: ReviewInput, db: Session = Depends(session)):
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(404, "Incident not found")
        if incident.state != "review-ready":
            raise HTTPException(409, "Review requires review-ready state")
        before = incident.review
        incident.review = item.model_dump()
        incident.updated_at = now()
        record(db, "incident.reviewed", "incident", incident.id, before=before, after=incident.review)
        db.commit()
        return {"review": incident.review}

    @app.post("/incidents/{incident_id}/transition")
    def transition(incident_id: int, item: TransitionInput, db: Session = Depends(session)):
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(404, "Incident not found")
        allowed = {"triage": "investigating", "investigating": "review-ready", "review-ready": "approved"}
        if allowed.get(incident.state) != item.state:
            raise HTTPException(409, "Invalid lifecycle transition")
        if item.state == "approved":
            if not (incident.review or {}).get("human_approved"):
                raise HTTPException(409, "Explicit human approval required")
            # Check the full publication gate against a temporary approved state.
            incident.state = "approved"
            try:
                build_public_record(db, incident)
            except HTTPException:
                incident.state = "review-ready"
                raise
        else:
            incident.state = item.state
        incident.updated_at = now()
        record(db, "incident.transitioned", "incident", incident.id, before={"state": next(k for k, v in allowed.items() if v == item.state)}, after={"state": item.state}, reason=item.reason)
        db.commit()
        return {"id": incident.id, "state": incident.state}

    @app.get("/incidents/{incident_id}/preview")
    def preview(incident_id: int, db: Session = Depends(session)):
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(404, "Incident not found")
        return build_public_record(db, incident)

    @app.post("/incidents/{incident_id}/export")
    def export(incident_id: int, item: ExportInput, db: Session = Depends(session)):
        if not item.acknowledged:
            raise HTTPException(409, "Explicit export acknowledgment required")
        incident = db.get(Incident, incident_id)
        if not incident:
            raise HTTPException(404, "Incident not found")
        public = build_public_record(db, incident)
        write_export(export_dir, public)
        record(db, "incident.exported", "incident", incident.id, after=public, reason="Explicit analyst export")
        db.commit()
        return {"record": public}

    @app.post("/incidents/{incident_id}/evidence", status_code=201)
    def add_evidence(incident_id: int, item: EvidenceInput, db: Session = Depends(session)):
        incident = db.get(Incident, incident_id)
        if not incident or not db.get(Source, item.source_id):
            raise HTTPException(404, "Incident or source not found")
        if incident.state in ("approved", "published", "withdrawn"):
            raise HTTPException(409, "Approved incident is locked")
        incident.review = {}
        incident.updated_at = now()
        evidence = Evidence(incident_id=incident_id, **item.model_dump(), digest=hashlib.sha256(item.text.encode()).hexdigest())
        db.add(evidence)
        db.flush()
        record(db, "evidence.created", "evidence", evidence.id, after={"digest": evidence.digest, "incident_id": incident_id})
        db.commit()
        return {"id": evidence.id, "digest": evidence.digest}

    @app.get("/incidents/{incident_id}/evidence")
    def list_evidence(incident_id: int, db: Session = Depends(session)):
        if not db.get(Incident, incident_id):
            raise HTTPException(404, "Incident not found")
        return [{"id": e.id, "source_id": e.source_id, "url": e.url, "text": e.text, "published_at": e.published_at} for e in db.scalars(select(Evidence).where(Evidence.incident_id == incident_id))]

    @app.get("/audit")
    def list_audit(db: Session = Depends(session)):
        return [{"id": a.id, "action": a.action, "entity": a.entity, "entity_id": a.entity_id, "timestamp": a.timestamp, "before_hash": a.before_hash, "after_hash": a.after_hash, "reason": a.reason} for a in db.scalars(select(Audit).order_by(Audit.id))]

    return app
