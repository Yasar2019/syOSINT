import hashlib
import ipaddress
import os
from threading import Lock
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .candidate_review import (
    CandidateConflict, CandidateNotFound, candidate_response, review_response,
    normalize_candidate_url, create_candidate, review_candidate,
)
from .db import database, record
from .export import build_public_record, write_export
from .models import (
    Audit,
    SourceCandidate,
    CandidateReview,
    Evidence,
    FeedCursor,
    IntakeItem,
    IntakeQuarantine,
    Incident,
    Source,
    TelegramCursor,
    TelegramPublication,
    TelegramPublicationPreview,
    now,
)
from .rss_scheduler import RssScheduler, default_collector
from .rss_store import store_collection
from .safe_http import HttpValidators
from .telegram_collect import ChannelPolicyError, resolve_public_channel, sync_channel
from .telegram_session import TelegramSettings, safe_auth_state
from .telegram_publication import (
    PublicationConflict, PublicationPayload, approve_publication,
    build_publication_preview, correct_publication, withdraw_publication,
    publication_attention,
)
from .telegram_export import PublicSchemaError, write_pending_telegram_export
from .telegram_scheduler import TelegramScheduler


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


class CandidateCreate(Strict):
    platform: Literal["web", "telegram"]
    url: str = Field(min_length=1, max_length=2048)
    name: str = Field(min_length=1, max_length=250)
    language: Literal["en", "ar", "mixed"]
    suggestion_reason: str = Field(min_length=1, max_length=1000)

    @field_validator("name", "suggestion_reason")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("A nonblank value is required")
        return value

    @model_validator(mode="after")
    def validate_url(self):
        normalize_candidate_url(self.platform, self.url)
        return self


class CandidateChecks(Strict):
    accessibility_checked: StrictBool
    relevance_checked: StrictBool
    identity_checked: StrictBool
    provenance_checked: StrictBool
    policy_checked: StrictBool


class CandidateReviewCreate(Strict):
    decision: Literal["accepted", "rejected"]
    reason: str = Field(min_length=1, max_length=1000)
    checks: CandidateChecks

    @model_validator(mode="after")
    def validate_review(self):
        if not self.reason.strip():
            raise ValueError("A review reason is required")
        if self.decision == "accepted" and not all(self.checks.model_dump().values()):
            raise ValueError("Acceptance requires all five human checks")
        return self


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


class TelegramResolveInput(Strict):
    username: str = Field(min_length=5, max_length=32)


class TelegramChannelInput(TelegramResolveInput):
    channel_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=250)
    language: Literal["en", "ar", "mixed"]


class TelegramMediaPolicyInput(Strict):
    enabled: bool



class PublicationPreviewInput(Strict):
    headline_en: str = Field(min_length=3, max_length=240)
    headline_ar: str = Field(min_length=3, max_length=240)
    source_identity_checked: bool
    person_safety_checked: bool
    operational_safety_checked: bool
    human_approved: bool


class PublicationApprovalInput(PublicationPreviewInput):
    draft_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class PublicationCorrectionInput(PublicationPreviewInput):
    reason_en: str = Field(min_length=3, max_length=240)
    reason_ar: str = Field(min_length=3, max_length=240)


class PublicationWithdrawalInput(Strict):
    reason_en: str = Field(min_length=3, max_length=240)
    reason_ar: str = Field(min_length=3, max_length=240)
    human_approved: bool


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
        telegram_scheduler = None
        if os.environ.get("SYOSINT_RSS_SCHEDULER", "1") != "0":
            scheduler = RssScheduler(engine)
            app.state.rss_scheduler = scheduler
            scheduler.start()
        if os.environ.get("SYOSINT_TELEGRAM_SCHEDULER", "1") != "0":
            try:
                settings = TelegramSettings.load()
                if settings.configured:
                    with Session(engine) as db:
                        has_source = db.scalar(select(Source.id).where(
                            Source.kind == "telegram", Source.enabled.is_(True),
                        ).limit(1)) is not None
                    if has_source:
                        telegram_scheduler = TelegramScheduler(engine, settings)
                        app.state.telegram_scheduler = telegram_scheduler
                        telegram_scheduler.start()
            except (ValueError, OSError):
                # Invalid Telegram-only configuration cannot stop the local API.
                pass
        try:
            yield
        finally:
            if telegram_scheduler is not None:
                await telegram_scheduler.stop()
            if scheduler is not None:
                await scheduler.stop()

    app = FastAPI(title="syOSINT local analyst API", lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
    app.state.export_dir = export_dir
    app.state.engine = engine
    publication_lock = Lock()

    def session():
        with Session(engine) as db:
            yield db

    def telegram_transport():
        try:
            settings = TelegramSettings.load()
        except (ValueError, OSError):
            raise HTTPException(503, "Telegram not configured") from None
        if not settings.configured:
            raise HTTPException(503, "Telegram not configured")
        factory = getattr(app.state, "telegram_transport_factory", None)
        if factory is None:
            from .telegram_scheduler import TelethonReadTransport
            factory = lambda: TelethonReadTransport(settings)
        try:
            return factory()
        except Exception:
            raise HTTPException(503, "Telegram temporarily unavailable") from None

    async def close_telegram(transport):
        disconnect = getattr(transport, "disconnect", None)
        if disconnect is not None:
            try:
                await disconnect()
            except Exception:
                pass

    @app.post("/candidates", status_code=201)
    def add_candidate(item: CandidateCreate, db: Session = Depends(session)):
        try:
            return create_candidate(db, **item.model_dump())
        except CandidateConflict as exc:
            raise HTTPException(409, {"kind": exc.kind, "id": exc.existing_id}) from None

    @app.get("/candidates")
    def list_candidates(status: Literal["pending", "accepted", "rejected"] | None = None,
                        limit: int = Query(default=100, ge=1, le=100),
                        offset: int = Query(default=0, ge=0), db: Session = Depends(session)):
        query = select(SourceCandidate)
        if status is not None:
            query = query.where(SourceCandidate.status == status)
        return [candidate_response(row) for row in db.scalars(
            query.order_by(SourceCandidate.id.desc()).limit(limit).offset(offset))]

    @app.get("/candidates/{candidate_id}")
    def get_candidate(candidate_id: int, db: Session = Depends(session)):
        candidate = db.get(SourceCandidate, candidate_id)
        if candidate is None:
            raise HTTPException(404, "Candidate not found")
        reviews = db.scalars(select(CandidateReview).where(
            CandidateReview.candidate_id == candidate_id).order_by(CandidateReview.id))
        return {**candidate_response(candidate), "reviews": [review_response(row) for row in reviews]}

    @app.post("/candidates/{candidate_id}/reviews", status_code=201)
    def add_candidate_review(candidate_id: int, item: CandidateReviewCreate,
                             db: Session = Depends(session)):
        try:
            return review_candidate(db, candidate_id, decision=item.decision,
                                    reason=item.reason, checks=item.checks.model_dump())
        except CandidateNotFound:
            raise HTTPException(404, "Candidate not found") from None

    @app.get("/telegram/status")
    async def telegram_status():
        try:
            settings = TelegramSettings.load()
            state = safe_auth_state(settings)
        except (ValueError, OSError):
            state = "not-configured"
        if state != "not-configured":
            try:
                transport = telegram_transport()
            except HTTPException:
                return {"state": "reauthentication-required"}
            try:
                if await transport.is_authorized():
                    state = "authenticated"
            except Exception:
                state = "reauthentication-required"
            finally:
                await close_telegram(transport)
        return {"state": state}

    @app.post("/telegram/channels/resolve")
    async def resolve_telegram_channel(item: TelegramResolveInput):
        transport = telegram_transport()
        try:
            channel = await resolve_public_channel(item.username, transport)
            return {"channel_id": channel.channel_id, "username": channel.username,
                    "title": channel.title}
        except ChannelPolicyError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception:
            raise HTTPException(503, "Telegram temporarily unavailable") from None
        finally:
            await close_telegram(transport)

    @app.post("/telegram/channels", status_code=201)
    async def approve_telegram_channel(item: TelegramChannelInput, db: Session = Depends(session)):
        transport = telegram_transport()
        try:
            channel = await resolve_public_channel(item.username, transport)
        except ChannelPolicyError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception:
            raise HTTPException(503, "Telegram temporarily unavailable") from None
        finally:
            await close_telegram(transport)
        if channel.channel_id != item.channel_id or channel.title != item.title:
            raise HTTPException(409, "Channel identity changed; resolve again")
        url = f"https://t.me/{channel.username}"
        if db.scalar(select(Source).where(Source.url == url)):
            raise HTTPException(409, "Channel already approved")
        source = Source(name=channel.title, url=url, language=item.language,
                        kind="telegram", public_identifier=channel.username,
                        enabled=True, media_enabled=False)
        db.add(source)
        db.flush()
        db.add(TelegramCursor(source_id=source.id, channel_id=channel.channel_id))
        record(db, "telegram.channel.approved", "source", source.id,
               after={"username": channel.username, "language": item.language})
        db.commit()
        return {"id": source.id, "username": channel.username,
                "name": channel.title, "language": item.language, "enabled": True}

    @app.get("/telegram/channels")
    def list_telegram_channels(db: Session = Depends(session)):
        return [{"id": source.id, "name": source.name,
                 "username": source.public_identifier, "language": source.language,
                 "enabled": source.enabled, "media_enabled": source.media_enabled,
                 "status": (cursor.last_status if (cursor := db.get(TelegramCursor, source.id)) else None),
                 "last_success_at": cursor.last_success_at if cursor else None}
                for source in db.scalars(select(Source).where(Source.kind == "telegram").order_by(Source.id))]

    @app.put("/telegram/channels/{source_id}/media-policy")
    def update_telegram_media_policy(source_id: int, item: TelegramMediaPolicyInput,
                                     db: Session = Depends(session)):
        source = db.get(Source, source_id)
        if source is None or source.kind != "telegram":
            raise HTTPException(404, "Approved channel not found")
        previous = bool(source.media_enabled)
        source.media_enabled = item.enabled
        record(db, "telegram.media.policy.changed", "source", source_id,
               before={"enabled": previous}, after={"enabled": item.enabled})
        db.commit()
        return {"enabled": item.enabled}

    @app.post("/telegram/channels/{source_id}/sync")
    async def sync_telegram_channel(source_id: int, db: Session = Depends(session)):
        source = db.get(Source, source_id)
        if source is None or source.kind != "telegram" or not source.enabled:
            raise HTTPException(404, "Approved channel not found")
        db.expunge(source)
        transport = telegram_transport()
        try:
            summary = await sync_channel(engine, source_id, transport, now())
            return {"created": summary.created, "duplicates": summary.duplicates,
                    "quarantined": summary.quarantined}
        except ChannelPolicyError as exc:
            raise HTTPException(409, str(exc)) from None
        except Exception:
            raise HTTPException(503, "Telegram temporarily unavailable") from None
        finally:
            await close_telegram(transport)


    def pending_telegram_export(db: Session):
        records = [publication.record for publication in db.scalars(
            select(TelegramPublication).order_by(TelegramPublication.id))]
        pending_path = app.state.export_dir / "telegram-pending.v1.json"
        try:
            # If rewriting fails, an old artifact must not be stageable after
            # a committed correction or withdrawal.
            if pending_path.parent.is_symlink():
                raise PublicSchemaError("unsafe pending export directory")
            pending_path.unlink(missing_ok=True)
            write_pending_telegram_export(app.state.export_dir, records, now())
        except (OSError, ValueError, PublicSchemaError):
            raise HTTPException(503, "Pending editorial export unavailable") from None

    @app.post("/telegram-publications/export-pending")
    def rebuild_pending_telegram_export(db: Session = Depends(session)):
        with publication_lock:
            pending_telegram_export(db)
        return {"status": "pending-export-ready"}

    @app.get("/telegram-publication-previews/{draft_hash}")
    def get_telegram_publication_preview(draft_hash: str, db: Session = Depends(session)):
        if len(draft_hash) != 64 or any(character not in "0123456789abcdef" for character in draft_hash):
            raise HTTPException(404, "Preview unavailable")
        draft = db.scalar(select(TelegramPublicationPreview).where(
            TelegramPublicationPreview.draft_hash == draft_hash))
        if draft is None or (draft.expires_at.replace(tzinfo=UTC) if draft.expires_at.tzinfo is None else draft.expires_at) < now():
            raise HTTPException(404, "Preview expired; review again")
        return {"item_id": draft.item_id, "draft_hash": draft.draft_hash, "record": draft.record}

    @app.get("/intake-items/{item_id}/publication")
    def get_telegram_publication(item_id: int, db: Session = Depends(session)):
        publication = db.scalar(select(TelegramPublication).where(
            TelegramPublication.item_id == item_id))
        if publication is None:
            raise HTTPException(404, "Publication unavailable")
        return {"id": publication.id, "public_id": publication.public_id,
                "status": publication.status, "record": publication.record}

    @app.post("/intake-items/{item_id}/publication-preview")
    def preview_telegram_publication(item_id: int, item: PublicationPreviewInput,
                                     db: Session = Depends(session)):
        try:
            draft = build_publication_preview(
                db, item_id, PublicationPayload(**item.model_dump()))
        except PublicationConflict as error:
            raise HTTPException(409, str(error)) from None
        return {"draft_hash": draft.draft_hash, "record": draft.record}

    @app.post("/intake-items/{item_id}/publication-approve")
    def approve_telegram_publication(item_id: int, item: PublicationApprovalInput,
                                     db: Session = Depends(session)):
        draft = db.scalar(select(TelegramPublicationPreview).where(
            TelegramPublicationPreview.draft_hash == item.draft_hash))
        if draft is None or draft.item_id != item_id:
            raise HTTPException(409, "Preview belongs to a different item")
        with publication_lock:
            # The preview ownership read happened outside this lock. Start a
            # fresh transaction so capacity checks see preceding approvals.
            db.rollback()
            try:
                publication = approve_publication(
                    db, item.draft_hash, PublicationPayload(**item.model_dump(exclude={"draft_hash"})))
            except PublicationConflict as error:
                raise HTTPException(409, str(error)) from None
            pending_telegram_export(db)
        return {"id": publication.id, "public_id": publication.public_id, "status": publication.status}

    @app.post("/telegram-publications/{publication_id}/correct")
    def correct_telegram_publication(publication_id: int, item: PublicationCorrectionInput,
                                     db: Session = Depends(session)):
        with publication_lock:
            try:
                publication = correct_publication(
                    db, publication_id,
                    PublicationPayload(**item.model_dump(exclude={"reason_en", "reason_ar"})),
                    item.reason_en, item.reason_ar)
            except PublicationConflict as error:
                raise HTTPException(409, str(error)) from None
            pending_telegram_export(db)
        return {"id": publication.id, "public_id": publication.public_id, "status": publication.status}

    @app.post("/telegram-publications/{publication_id}/withdraw")
    def withdraw_telegram_publication(publication_id: int, item: PublicationWithdrawalInput,
                                      db: Session = Depends(session)):
        with publication_lock:
            try:
                publication = withdraw_publication(
                    db, publication_id, item.reason_en, item.reason_ar, item.human_approved)
            except PublicationConflict as error:
                raise HTTPException(409, str(error)) from None
            pending_telegram_export(db)
        return {"id": publication.id, "public_id": publication.public_id, "status": publication.status}

    @app.get("/telegram-publications/attention")
    def list_telegram_publication_attention(db: Session = Depends(session)):
        return publication_attention(db)

    @app.middleware("http")
    async def enforce_local_origin(request, call_next):
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS") and origin and origin not in ("http://127.0.0.1:3001", "http://localhost:3001"):
            return JSONResponse({"detail": "Untrusted origin"}, status_code=403)
        return await call_next(request)

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
    @app.get("/intake-items")
    def list_intake_items(
        request: Request,
        status: Literal["new", "promoted", "attached", "duplicate", "quarantined"] = "new",
        db: Session = Depends(session),
    ):
        rss_only = request.url.path == "/feed-items"
        if status == "quarantined":
            query = select(IntakeQuarantine).order_by(IntakeQuarantine.id.desc())
            if rss_only:
                query = query.where(IntakeQuarantine.platform == "rss")
            return [
                {
                    "id": item.id,
                    "source_id": item.source_id,
                    "status": "quarantined",
                    "headline": item.headline,
                    "reason": item.reason,
                    "collected_at": item.created_at,
                    **({} if rss_only else {"platform": item.platform, "native_id": item.native_id}),
                }
                for item in db.scalars(query)
            ]
        query = select(IntakeItem).where(IntakeItem.status == status).order_by(
            IntakeItem.published_at.desc(), IntakeItem.id.desc()
        )
        if rss_only:
            query = query.where(IntakeItem.platform == "rss")
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
                **({} if rss_only else {
                    "platform": item.platform,
                    "native_id": item.native_id,
                    "edited_at": item.edited_at,
                    "deleted_at": item.deleted_at,
                }),
            }
            for item in db.scalars(query)
        ]

    def add_feed_evidence(db: Session, item: IntakeItem, incident: Incident):
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
    @app.post("/intake-items/{item_id}/promote", status_code=201)
    def promote_feed_item(
        item_id: int,
        payload: PromoteFeedItemInput,
        response: Response,
        request: Request,
        db: Session = Depends(session),
    ):
        item = db.get(IntakeItem, item_id)
        if not item or (request.url.path.startswith("/feed-items/") and item.platform != "rss"):
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
    @app.post("/intake-items/{item_id}/attach")
    def attach_feed_item(
        item_id: int,
        payload: AttachFeedItemInput,
        request: Request,
        db: Session = Depends(session),
    ):
        item = db.get(IntakeItem, item_id)
        incident = db.get(Incident, payload.incident_id)
        if not item or not incident or (request.url.path.startswith("/feed-items/") and item.platform != "rss"):
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
