"""Inert private leads; no source activation or remote I/O."""
import ipaddress
import re
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .db import record
from .models import CandidateReview, Source, SourceCandidate, now


class CandidateConflict(Exception):
    def __init__(self, kind: str, existing_id: int):
        self.kind = kind
        self.existing_id = existing_id
        super().__init__('Candidate conflicts with an existing record')


class CandidateNotFound(Exception):
    pass


def normalize_candidate_url(platform: Literal['web', 'telegram'], url: str) -> str:
    if platform not in ('web', 'telegram'):
        raise ValueError('Invalid candidate platform')
    if len(url) > 2048 or any(char.isspace() or ord(char) < 32 for char in url) or '\\' in url:
        raise ValueError('Use a public HTTPS URL')
    parsed = urlsplit(url)
    host = (parsed.hostname or '').lower()
    # Validate DNS labels without resolving the lead. Numeric final labels can
    # be interpreted as abbreviated/octal/hex IPv4 by HTTP clients and browsers.
    dns_host = host.removesuffix('.')
    try:
        ascii_host = dns_host.encode('idna').decode('ascii').lower()
    except UnicodeError:
        raise ValueError('Use a valid public DNS hostname') from None
    labels = ascii_host.split('.')
    if (len(ascii_host) > 253 or len(labels) < 2 or
        any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
            for label in labels) or
        re.fullmatch(r'(?:[0-9]+|0[xX][0-9A-Fa-f]+)', labels[-1])):
        raise ValueError('Use a valid public DNS hostname, not a numeric IP reference')
    if ascii_host.lower() == 't.me' and platform != 'telegram':
        raise ValueError('Telegram links require the Telegram platform')
    try:
        ipaddress.ip_address(ascii_host)
    except ValueError:
        pass
    else:
        raise ValueError('IP address references are not allowed')
    if (parsed.scheme != 'https' or not host or '.' not in host or
        ascii_host.endswith(('.local', '.localhost', '.internal')) or
        ascii_host == 'localhost' or parsed.username is not None or
        parsed.password is not None or '#' in url or parsed.port not in (None, 443)):
        raise ValueError('Use a public HTTPS reference without credentials or fragments')
    path = '' if parsed.path == '/' else parsed.path
    if platform == 'telegram':
        if host != 't.me' or parsed.port is not None or parsed.query or not re.fullmatch(r'/[A-Za-z][A-Za-z0-9_]{4,31}', path):
            raise ValueError('Use a public Telegram username link')
        path = path.lower()
    # Preserve an explicitly supplied HTTPS port and all non-root web paths/queries.
    authority = host + (':443' if parsed.port == 443 else '')
    return urlunsplit(('https', authority, path, parsed.query, ''))


def candidate_response(candidate: SourceCandidate) -> dict:
    return {key: getattr(candidate, key) for key in (
        'id', 'platform', 'canonical_url', 'name', 'language', 'suggestion_reason',
        'status', 'created_at', 'updated_at')}


def review_response(review: CandidateReview) -> dict:
    return {key: getattr(review, key) for key in (
        'id', 'candidate_id', 'decision', 'reason', 'checks', 'created_at')}


def create_candidate(db: Session, *, platform: str, url: str, name: str,
                     language: str, suggestion_reason: str) -> dict:
    canonical_url = normalize_candidate_url(platform, url)
    query = select(SourceCandidate).where(SourceCandidate.platform == platform,
                                          SourceCandidate.canonical_url == canonical_url)
    existing = db.scalar(query)
    if existing is not None:
        raise CandidateConflict('candidate', existing.id)
    for source in db.scalars(select(Source)):
        source_platform = 'telegram' if source.kind == 'telegram' else 'web'
        if source_platform != platform:
            continue
        try:
            registered_url = normalize_candidate_url(source_platform, source.url)
        except ValueError:
            continue
        if registered_url == canonical_url:
            raise CandidateConflict('source', source.id)
    candidate = SourceCandidate(platform=platform, canonical_url=canonical_url,
                                name=name, language=language, suggestion_reason=suggestion_reason)
    db.add(candidate)
    try:
        db.flush()
        record(db, 'candidate.created', 'candidate', candidate.id,
               after=candidate_response(candidate))
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(query)
        if existing is None:
            raise
        raise CandidateConflict('candidate', existing.id) from None
    return candidate_response(candidate)


def review_candidate(db: Session, candidate_id: int, *, decision: str,
                     reason: str, checks: dict[str, bool]) -> dict:
    candidate = db.get(SourceCandidate, candidate_id)
    if candidate is None:
        raise CandidateNotFound()
    review = CandidateReview(candidate_id=candidate_id, decision=decision, reason=reason, checks=checks)
    previous = candidate.status
    candidate.status = decision
    candidate.updated_at = now()
    db.add(review)
    db.flush()
    record(db, 'candidate.reviewed', 'candidate', candidate_id,
           before={'status': previous}, after=review_response(review))
    db.commit()
    return review_response(review)
