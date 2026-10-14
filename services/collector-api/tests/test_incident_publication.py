from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from syosint.api import create_app
from syosint.models import Incident, Source, Evidence

FIELDS = dict(title_en='Synthetic report', title_ar='تقرير تجريبي', category='infrastructure', summary_en='Synthetic claim.', summary_ar='ادعاء تجريبي.', uncertainty_en='Uncertain.', uncertainty_ar='غير مؤكد.', location_en='Syria', location_ar='سوريا', precision='country', occurred_at='2026-09-23T10:00:00Z', confidence='unverified')
REVIEW = dict(rationale='Synthetic independent review.', **{k: True for k in ['independence_checked','time_checked','location_checked','contradictions_checked','person_safety_checked','operational_safety_checked','contradictions_acknowledged','human_approved']})

def setup(tmp_path):
    app = create_app(f'sqlite:///{tmp_path / "vault.sqlite"}', tmp_path / 'exports')
    with Session(app.state.engine) as db:
        s = Source(name='Synthetic', url='https://example.org', language='en'); db.add(s); db.flush()
        i = Incident(fields=FIELDS, review=REVIEW, state='approved'); db.add(i); db.flush()
        db.add(Evidence(incident_id=i.id, source_id=s.id, url='https://example.org/report', text='Synthetic private text', published_at=FIELDS['occurred_at'], digest='0'*64)); db.commit()
    return TestClient(app, base_url='http://127.0.0.1:8765')

def test_revision_workflow(tmp_path):
    c = setup(tmp_path); p='/incidents/1'
    assert c.get(p+'/publication').json()['version'] == 0
    original=c.post(p+'/export', json={'acknowledged':True}).json()['record']
    assert c.post(p+'/export', json={'acknowledged':True}).json()['record']==original
    fields={**FIELDS,'title_en':'Corrected synthetic report'}
    assert c.put(p+'/correction',json=dict(expected_version=1,fields=fields,reason_en='Correction reason',reason_ar='سبب التصحيح')).status_code==200
    assert c.get(p+'/preview').json()==original
    assert c.get(p+'/correction/preview').status_code==409
    assert c.post(p+'/correction/review',json={**REVIEW,'expected_version':1}).status_code==200
    preview=c.get(p+'/correction/preview').json()
    assert preview['record']['corrections'][-1]['changedFields']==['title']
    assert c.post(p+'/correction/approve',json=dict(expected_version=1,preview_hash=preview['preview_hash'],acknowledged=True)).status_code==200
    assert c.get(p+'/publication').json()['version']==2
    assert not (tmp_path/'exports'/'incident-1.json').exists()
    c.post(p+'/export',json={'acknowledged':True})
    withdrawal=c.post(p+'/withdrawal/preview',json=dict(expected_version=2,reason_en='Withdrawn after review',reason_ar='سحب بعد المراجعة')).json()
    assert c.post(p+'/withdrawal/approve',json=dict(expected_version=2,preview_hash=withdrawal['preview_hash'],acknowledged=True)).status_code==200
    assert not (tmp_path/'exports'/'incident-1.json').exists()
    exported=c.post(p+'/export',json={'acknowledged':True}).json()['record']
    assert exported['status']=='withdrawn' and exported['sources']==[]
    assert 'Synthetic claim' not in str(exported)
    assert len(c.get(p+'/publication').json()['history'])==3


def draft(c, **kwargs):
    return c.put('/incidents/1/correction',json=dict(expected_version=1,fields={**FIELDS,'title_en':'Revised synthetic report'},reason_en='Correction',reason_ar='تصحيح',**kwargs))


def test_stale_inputs_review_reset_and_isolation(tmp_path):
    c=setup(tmp_path); p='/incidents/1'
    assert draft(c).status_code==409
    original=c.post(p+'/export',json={'acknowledged':True}).json()['record']
    assert c.put(p+'/correction',json=dict(expected_version=1,fields={**FIELDS,'private_governorate':'aleppo'},reason_en='Private change',reason_ar='تغيير')).status_code==409
    for value in [True,0,-1,'1',1.1]:
        assert c.post(p+'/withdrawal/preview',json=dict(expected_version=value,reason_en='Reason',reason_ar='سبب')).status_code==422
    assert c.post(p+'/withdrawal/preview',json=dict(expected_version=1,reason_en=' ',reason_ar='سبب')).status_code==422
    assert c.post(p+'/withdrawal/preview',json=dict(expected_version=1,reason_en='Reason',reason_ar='سبب',evidence='forbidden')).status_code==422
    assert draft(c).status_code==200
    assert c.get(p).json()['title_en']==FIELDS['title_en']
    assert c.post(p+'/correction/review',json={**REVIEW,'expected_version':1,'person_safety_checked':False}).status_code==200
    assert c.get(p+'/correction/preview').status_code==409
    c.post(p+'/correction/review',json={**REVIEW,'expected_version':1})
    preview=c.get(p+'/correction/preview').json()
    for version,hash_value,ack in [(2,preview['preview_hash'],True),(1,'0'*64,True),(1,preview['preview_hash'],False)]:
        assert c.post(p+'/correction/approve',json=dict(expected_version=version,preview_hash=hash_value,acknowledged=ack)).status_code==409
    assert c.get(p+'/publication').json()['record']==original
    assert draft(c).status_code==200
    assert c.get(p+'/publication').json()['draft']['review']=={}
    assert c.post(p+'/correction/approve',json=dict(expected_version=1,preview_hash=preview['preview_hash'],acknowledged=True)).status_code==409
    assert c.get('/incidents/999/publication').status_code==404


def test_expiry_terminal_and_hash_invalidation(tmp_path):
    from datetime import timedelta
    from syosint.models import IncidentWithdrawalPreview, now
    c=setup(tmp_path);p='/incidents/1';c.post(p+'/export',json={'acknowledged':True})
    payload=dict(expected_version=1,reason_en='Withdrawn reason',reason_ar='سبب السحب')
    first=c.post(p+'/withdrawal/preview',json=payload).json()
    with Session(c.app.state.engine) as db:
        db.get(IncidentWithdrawalPreview,1).expires_at=now()-timedelta(seconds=1);db.commit()
    approve=dict(expected_version=1,preview_hash=first['preview_hash'],acknowledged=True)
    assert c.post(p+'/withdrawal/approve',json=approve).status_code==409
    second=c.post(p+'/withdrawal/preview',json=payload).json()
    assert c.post(p+'/withdrawal/approve',json=approve).status_code==409
    approve['preview_hash']=second['preview_hash']
    assert c.post(p+'/withdrawal/approve',json=approve).status_code==200
    assert c.post(p+'/withdrawal/approve',json=approve).status_code==409
    assert c.post(p+'/withdrawal/preview',json=payload).status_code==409
    assert draft(c).status_code==409
    assert len(c.get(p+'/publication').json()['history'])==2


def test_export_failure_retry_snapshot_and_concurrency(tmp_path,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from unittest.mock import Mock
    import syosint.api as api
    c=setup(tmp_path);p='/incidents/1';folder=tmp_path/'exports';folder.mkdir();old=folder/'incident-1.json';old.write_text('stale')
    writer=api.write_export
    monkeypatch.setattr(api,'write_export',Mock(side_effect=OSError('/private/path/secret')))
    response=c.post(p+'/export',json={'acknowledged':True})
    assert response.status_code==503 and '/private' not in response.text and not old.exists()
    frozen=c.get(p+'/publication').json()
    assert frozen['version']==1 and len(frozen['history'])==1
    monkeypatch.setattr(api,'write_export',writer)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _: c.post(p+'/export',json={'acknowledged':True}),range(8)))
    assert all(r.status_code==200 and r.json()['record']==frozen['record'] for r in results)
    assert len(c.get(p+'/publication').json()['history'])==1
    assert all('Synthetic private text' not in str(row) for row in c.get('/audit').json())


def test_populated_migration_upgrade_and_constraints(tmp_path):
    import sqlite3
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    import pytest
    from sqlalchemy.exc import IntegrityError
    from syosint.models import IncidentPublicationRevision
    root=Path(__file__).resolve().parents[1]
    path=tmp_path/'existing.sqlite'; cfg=Config(str(root/'alembic.ini'));cfg.set_main_option('sqlalchemy.url',f'sqlite:///{path}')
    command.upgrade(cfg,'0006')
    with sqlite3.connect(path) as conn:
        conn.execute("insert into incidents(fields,state,review,created_at,updated_at) values ('{}','triage','{}','2026-09-23','2026-09-23')")
    command.upgrade(cfg,'head')
    with sqlite3.connect(path) as conn:
        assert conn.execute('select count(*) from incidents').fetchone()[0]==1
        assert conn.execute('select version_num from alembic_version').fetchone()[0]=='0007'
        assert conn.execute('select count(*) from incident_publications').fetchone()[0]==0
    c=setup(tmp_path)
    c.post('/incidents/1/export',json={'acknowledged':True})
    with Session(c.app.state.engine) as db:
        db.add(IncidentPublicationRevision(incident_id=1,version=1,record={},action='published',reason_en='',reason_ar=''))
        with pytest.raises(IntegrityError):db.commit()


def test_review_changes_and_serialized_approval(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    c=setup(tmp_path);p='/incidents/1';c.post(p+'/export',json={'acknowledged':True});draft(c)
    c.post(p+'/correction/review',json={**REVIEW,'expected_version':1})
    first=c.get(p+'/correction/preview').json()
    c.post(p+'/correction/review',json={**REVIEW,'expected_version':1,'rationale':'Renewed synthetic review.'})
    assert c.post(p+'/correction/approve',json=dict(expected_version=1,preview_hash=first['preview_hash'],acknowledged=True)).status_code==409
    second=c.get(p+'/correction/preview').json()
    assert c.get(p+'/correction/preview').json()==second
    payload=dict(expected_version=1,preview_hash=second['preview_hash'],acknowledged=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(lambda _:c.post(p+'/correction/approve',json=payload).status_code,range(2)))
    assert sorted(statuses)==[200,409]
    result=c.get(p+'/publication').json()
    assert len(result['history'])==2 and result['history'][0]['record']['title']['en']==FIELDS['title_en']
    assert result['draft'] is None
    assert c.post(p+'/export',json={'acknowledged':True}).json()['record']==second['record']


def test_draft_can_request_new_confidence_and_requires_fresh_gate(tmp_path):
    c=setup(tmp_path);p='/incidents/1';c.post(p+'/export',json={'acknowledged':True})
    fields={**FIELDS,'confidence':'verified'}
    assert c.put(p+'/correction',json=dict(expected_version=1,fields=fields,reason_en='New assessment',reason_ar='تقييم جديد')).status_code==200
    c.post(p+'/correction/review',json={**REVIEW,'expected_version':1})
    assert c.get(p+'/correction/preview').status_code==409
    assert c.get(p+'/publication').json()['version']==1


def test_revision_cleanup_failure_keeps_approved_snapshot(tmp_path,monkeypatch):
    from pathlib import Path
    c=setup(tmp_path);p='/incidents/1';c.post(p+'/export',json={'acknowledged':True})
    preview=c.post(p+'/withdrawal/preview',json=dict(expected_version=1,reason_en='Synthetic withdrawal',reason_ar='سحب تجريبي')).json()
    unlink=Path.unlink
    def fail(self,*args,**kwargs):
        if self.name=='incident-1.json': raise OSError('/private/path')
        return unlink(self,*args,**kwargs)
    monkeypatch.setattr(Path,'unlink',fail)
    response=c.post(p+'/withdrawal/approve',json=dict(expected_version=1,preview_hash=preview['preview_hash'],acknowledged=True))
    assert response.status_code==503 and '/private' not in response.text
    assert c.get(p+'/publication').json()['version']==2
    monkeypatch.setattr(Path,'unlink',unlink)
    assert c.post(p+'/export',json={'acknowledged':True}).json()['record']['status']=='withdrawn'
