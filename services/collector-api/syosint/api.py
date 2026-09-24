import hashlib
import ipaddress
import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .db import database, record
from .export import build_public_record, write_export
from .models import (
    Audit,
    Evidence,
    FeedCursor,
    FeedItem,
    FeedQuarantine,
    Incident,
    Source,
    now,
)
from .rss_scheduler import RssScheduler, default_collector
from .rss_store import store_collection
from .safe_http import HttpValidators


INCIDENT_CATEGORIES = (
    "armed-conflict",
    "political-security",
    "humanitarian",
    "infrastructure",
    "border-crossing",
    "disinformation",
)


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


class FeedSourceInput(Strict):
    name: str = Field(min_length=1, max_length=250)
    url: str
    feed_url: str
    language: Literal["en", "ar"]
    enabled: bool = True
    poll_interval_minutes: int = Field(default=30, ge=15, le=1440)

    @field_validator("url", "feed_url")
    @classmethod
    def check_url(cls, value):
        return public_url(value)


class IncidentInput(Strict):
    title_en: str
    title_ar: str
    category: str


class PromoteFeedItemInput(IncidentInput):
    title_en: str = Field(min_length=3)
    title_ar: str = Field(min_length=3)

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        if value not in INCIDENT_CATEGORIES:
            raise ValueError("Invalid category")
        return value


class AttachFeedItemInput(Strict):
    incident_id: int = Field(gt=0)


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
        if value not in INCIDENT_CATEGORIES:
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
    primary_evidence_checked: bool = False


class TransitionInput(Strict):
    state: str
    reason: str = Field(min_length=8)


class ExportInput(Strict):
    acknowledged: bool


def create_app(database_url: str, export_dir: Path) -> FastAPI:
    engine = database(database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        scheduler = None
        if os.environ.get("SYOSINT_RSS_SCHEDULER", "1") != "0":
            scheduler = RssScheduler(engine)
            app.state.rss_scheduler = scheduler
            scheduler.start()
        try:
            yield
        finally:
            if scheduler is not None:
                await scheduler.stop()

    app = FastAPI(title="syOSINT local analyst API", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.state.export_dir = export_dir
    app.state.engine = engine

    @app.middleware("http")
    async def enforce_local_origin(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin not in ("http://127.0.0.1:3001", "http://localhost:3001"):
            return JSONResponse({"detail": "Untrusted origin"}, status_code=403)
        return await call_next(request)

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

    @app.post("/feeds", status_code=201)
    def add_feed(item: FeedSourceInput, db: Session = Depends(session)):
        if db.scalar(
            select(Source).where(
                (Source.url == item.url) | (Source.feed_url == item.feed_url)
            )
        ):
            raise HTTPException(409, "Feed source already exists")
        values = item.model_dump()
        source = Source(kind="rss", **values)
        db.add(source)
        db.flush()
        record(db, "feed.created", "source", source.id, after=values)
        db.commit()
        return {"id": source.id, **values}

    @app.get("/feeds")
    def list_feeds(db: Session = Depends(session)):
        result = []
        for source in db.scalars(
            select(Source).where(Source.kind == "rss").order_by(Source.id)
        ):
            cursor = db.get(FeedCursor, source.id)
            result.append(
                {
                    "id": source.id,
                    "name": source.name,
                    "url": source.url,
                    "feed_url": source.feed_url,
                    "language": source.language,
                    "enabled": source.enabled,
                    "poll_interval_minutes": source.poll_interval_minutes,
                    "health": {
                        "status": cursor.last_status if cursor else "pending",
                        "last_success_at": cursor.last_success_at if cursor else None,
                        "consecutive_failures": (
                            cursor.consecutive_failures if cursor else 0
                        ),
                        "last_error_category": (
                            cursor.last_error_category if cursor else None
                        ),
                    },
                }
            )
        return result

    @app.post("/feeds/{source_id}/collect")
    def collect_feed(source_id: int, db: Session = Depends(session)):
        source = db.get(Source, source_id)
        if not source or source.kind != "rss":
            raise HTTPException(404, "Feed source not found")
        cursor = db.get(FeedCursor, source.id)
        validators = (
            HttpValidators(cursor.etag, cursor.last_modified) if cursor else None
        )
        collected_at = now()
        outcome = default_collector(source, collected_at, validators)
        summary = store_collection(db, source, outcome, collected_at)
        return {
            "status": outcome.status,
            "created": summary.created,
            "duplicates": summary.duplicates,
            "quarantined": summary.quarantined,
            "error_category": outcome.error_category,
        }

    @app.get("/feed-items")
    def list_feed_items(
        status: Literal["new", "promoted", "attached", "duplicate", "quarantined"] = "new",
        db: Session = Depends(session),
    ):
        if status == "quarantined":
            return [
                {
                    "id": item.id,
                    "source_id": item.source_id,
                    "status": "quarantined",
                    "headline": item.headline,
                    "reason": item.reason,
                    "collected_at": item.created_at,
                }
                for item in db.scalars(
                    select(FeedQuarantine).order_by(FeedQuarantine.id.desc())
                )
            ]
        return [
            {
                "id": item.id,
                "source_id": item.source_id,
                "status": item.status,
                "headline": item.headline,
                "url": item.url,
                "text": item.text,
                "published_at": item.published_at,
                "collected_at": item.collected_at,
                "incident_id": item.incident_id,
            }
            for item in db.scalars(
                select(FeedItem)
                .where(FeedItem.status == status)
                .order_by(FeedItem.published_at.desc(), FeedItem.id.desc())
            )
        ]

    def add_feed_evidence(db: Session, item: FeedItem, incident: Incident):
        evidence = Evidence(
            incident_id=incident.id,
            source_id=item.source_id,
            url=item.url,
            text=item.text,
            published_at=item.published_at.isoformat(),
            digest=hashlib.sha256(item.text.encode()).hexdigest(),
        )
        db.add(evidence)
        db.flush()
        record(
            db,
            "evidence.created",
            "evidence",
            evidence.id,
            after={
                "digest": evidence.digest,
                "incident_id": incident.id,
                "source_id": item.source_id,
                "url": item.url,
                "published_at": evidence.published_at,
            },
        )
        return evidence

    @app.post("/feed-items/{item_id}/promote", status_code=201)
    def promote_feed_item(
        item_id: int,
        payload: PromoteFeedItemInput,
        response: Response,
        db: Session = Depends(session),
    ):
        item = db.get(FeedItem, item_id)
        if not item:
            raise HTTPException(404, "Feed item not found")
        if item.status == "promoted" and item.incident_id:
            response.status_code = 200
            return {"incident_id": item.incident_id, "status": item.status}
        if item.status != "new":
            raise HTTPException(409, "Feed item is already resolved")
        incident = Incident(fields=payload.model_dump(), state="triage")
        db.add(incident)
        db.flush()
        record(
            db,
            "incident.created",
            "incident",
            incident.id,
            after=payload.model_dump(),
        )
        add_feed_evidence(db, item, incident)
        item.status = "promoted"
        item.incident_id = incident.id
        record(
            db,
            "feed_item.promoted",
            "feed_item",
            item.id,
            before={"status": "new"},
            after={"status": "promoted", "incident_id": incident.id},
        )
        db.commit()
        return {"incident_id": incident.id, "status": item.status}

    @app.post("/feed-items/{item_id}/attach")
    def attach_feed_item(
        item_id: int,
        payload: AttachFeedItemInput,
        db: Session = Depends(session),
    ):
        item = db.get(FeedItem, item_id)
        incident = db.get(Incident, payload.incident_id)
        if not item or not incident:
            raise HTTPException(404, "Feed item or incident not found")
        if incident.state in ("approved", "published", "withdrawn"):
            raise HTTPException(409, "Approved incident is locked")
        if item.status == "attached" and item.incident_id == incident.id:
            return {"incident_id": incident.id, "status": item.status}
        if item.status != "new":
            raise HTTPException(409, "Feed item is already resolved")
        add_feed_evidence(db, item, incident)
        incident.review = {}
        incident.updated_at = now()
        item.status = "attached"
        item.incident_id = incident.id
        record(
            db,
            "feed_item.attached",
            "feed_item",
            item.id,
            before={"status": "new"},
            after={"status": "attached", "incident_id": incident.id},
        )
        db.commit()
        return {"incident_id": incident.id, "status": item.status}

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
        if "latitude" in fields or "longitude" in fields:
            raise HTTPException(422, "Exact coordinates cannot be included in this release")
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
        source = db.get(Source, item.source_id)
        if not incident or not source:
            raise HTTPException(404, "Incident or source not found")
        source_host = urlsplit(source.url).hostname or ""
        reference_host = urlsplit(item.url).hostname or ""
        if reference_host != source_host and not reference_host.endswith("." + source_host):
            raise HTTPException(422, "Evidence URL must belong to its registered public source")
        if incident.state in ("approved", "published", "withdrawn"):
            raise HTTPException(409, "Approved incident is locked")
        incident.review = {}
        incident.updated_at = now()
        evidence = Evidence(incident_id=incident_id, **item.model_dump(), digest=hashlib.sha256(item.text.encode()).hexdigest())
        db.add(evidence)
        db.flush()
        record(db, "evidence.created", "evidence", evidence.id, after={"digest": evidence.digest, "incident_id": incident_id, "source_id": item.source_id, "url": item.url, "published_at": item.published_at})
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
