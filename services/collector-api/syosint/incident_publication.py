"""Private, versioned publication records. Call mutations under the app lock."""
from copy import deepcopy
from datetime import timezone
from fastapi import HTTPException
from sqlalchemy import select
from .db import digest, record
from .export import build_public_record, validate_public_record
from .models import Incident, IncidentPublication, IncidentPublicationRevision, IncidentCorrectionDraft, IncidentWithdrawalPreview, now


def timestamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


def require_incident(db, incident_id):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(404, 'Incident not found')
    return incident


def active(db, incident_id, version):
    require_incident(db, incident_id)
    publication = db.get(IncidentPublication, incident_id)
    if publication is None or publication.version != version:
        raise HTTPException(409, 'Publication version unavailable or stale')
    if publication.record['status'] == 'withdrawn':
        raise HTTPException(409, 'Withdrawal is terminal')
    return publication


def append(db, incident_id, public, action, reason_en='', reason_ar=''):
    validate_public_record(public)
    publication = db.get(IncidentPublication, incident_id)
    before = deepcopy(publication.record) if publication else None
    version = publication.version + 1 if publication else 1
    if publication:
        publication.version = version
        publication.record = deepcopy(public)
    else:
        publication = IncidentPublication(incident_id=incident_id, version=version, record=deepcopy(public))
        db.add(publication)
    db.add(IncidentPublicationRevision(incident_id=incident_id, version=version, record=deepcopy(public), action=action, reason_en=reason_en, reason_ar=reason_ar))
    record(db, 'incident.'+action, 'incident', incident_id, before=before, after=public, reason=reason_en)
    return publication


def changed_fields(current, candidate):
    return sorted(key for key in candidate if key not in ('updatedAt','status','corrections') and candidate[key] != current.get(key))


def submitted_projection(current, fields):
    """Compare editable public values without bypassing the later review gate."""
    candidate = deepcopy(current)
    for public, private in [('title', 'title'), ('summary', 'summary'), ('uncertainty', 'uncertainty')]:
        candidate[public] = dict(en=fields[private + '_en'], ar=fields[private + '_ar'])
    candidate['location'] = dict(en=fields['location_en'], ar=fields['location_ar'], precision=fields['precision'])
    candidate['categories'] = [fields['category']]
    candidate['occurredAt'] = fields['occurred_at']
    candidate['confidence'] = fields['confidence']
    return candidate


def projection(db, incident, fields, review, updated_at):
    detached = Incident(id=incident.id, fields=fields, review=review, state='approved', updated_at=updated_at)
    return build_public_record(db, detached)


def correction_preview(db, incident_id):
    draft = db.get(IncidentCorrectionDraft, incident_id)
    if draft is None:
        raise HTTPException(409, 'Correction draft unavailable')
    publication = active(db, incident_id, draft.base_version)
    public = projection(db, require_incident(db, incident_id), draft.fields, draft.review, draft.updated_at)
    changes = changed_fields(publication.record, public)
    if not changes:
        raise HTTPException(409, 'Correction requires a public change')
    public['status'] = 'corrected'
    public['corrections'] = deepcopy(publication.record['corrections']) + [dict(correctedAt=timestamp(draft.updated_at), reason=dict(en=draft.reason_en, ar=draft.reason_ar), changedFields=changes)]
    validate_public_record(public)
    return dict(record=public, preview_hash=digest(public), version=publication.version)


def clear_previews(db, incident_id, draft=False):
    classes = [IncidentWithdrawalPreview] + ([IncidentCorrectionDraft] if draft else [])
    for cls in classes:
        value = db.get(cls, incident_id)
        if value:
            db.delete(value)


def publication_response(db, incident_id):
    require_incident(db, incident_id)
    publication = db.get(IncidentPublication, incident_id)
    draft = db.get(IncidentCorrectionDraft, incident_id)
    history = db.scalars(select(IncidentPublicationRevision).where(IncidentPublicationRevision.incident_id == incident_id).order_by(IncidentPublicationRevision.version)).all()
    return dict(version=publication.version if publication else 0, record=publication.record if publication else None, history=[dict(version=h.version, action=h.action, reason=dict(en=h.reason_en, ar=h.reason_ar), created_at=timestamp(h.created_at), record=h.record) for h in history], draft=dict(base_version=draft.base_version, fields=draft.fields, review=draft.review, reason_en=draft.reason_en, reason_ar=draft.reason_ar) if draft else None)


def tombstone(publication, reason_en, reason_ar):
    when = timestamp(now())
    public = dict(id=publication.record['id'], status='withdrawn', categories=publication.record['categories'], confidence='unverified', occurredAt=when, updatedAt=when, title=dict(en='Withdrawn report',ar='تقرير مسحوب'), summary=dict(en=reason_en,ar=reason_ar), uncertainty=dict(en='This report has been withdrawn.',ar='تم سحب هذا التقرير.'), location=dict(en='Withheld',ar='محجوب',precision='withheld'), sourceCount=0, sources=[], corrections=[dict(correctedAt=when,reason=dict(en=reason_en,ar=reason_ar),changedFields=['status'])])
    validate_public_record(public)
    return public
