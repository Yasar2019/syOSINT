from datetime import UTC, datetime, timedelta
from sqlalchemy.orm import Session
from syosint.db import database
from syosint.models import Source, IntakeItem
from syosint.retention import run_retention, place_hold, release_hold

NOW = datetime(2026, 11, 9, tzinfo=UTC)

def test_preview_apply_hold_and_cutoff(tmp_path):
    engine = database(f"sqlite:///{tmp_path / 'synthetic.db'}")
    with Session(engine) as db:
        source = Source(name='synthetic', url='https://example.org', language='en')
        db.add(source); db.flush()
        for i, days in enumerate((181,180)):
            db.add(IntakeItem(source_id=source.id, fingerprint=str(i), url=f'https://example.org/{i}', text='synthetic', published_at=NOW, collected_at=NOW-timedelta(days=days), raw_digest='a'*64))
        db.commit()
    assert run_retention(engine,tmp_path,NOW)['intake'] == 1
    with Session(engine) as db:
        assert db.get(IntakeItem,1)
    hold = place_hold(engine,'intake',1,' preserve ',NOW)
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake'] == 0
    release_hold(engine,hold['id'],'done',NOW)
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake'] == 1
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake'] == 0

import os
import pytest
from sqlalchemy import select
from syosint.models import MediaAsset, Audit, RetentionRun, IntakeRevision, Evidence, Incident, TelegramPublicationPreview, IntakeQuarantine
from syosint.retention import safe_file, RetentionError


def seed(tmp_path, *, days=181):
    engine = database(f"sqlite:///{tmp_path / 'synthetic.db'}")
    with Session(engine) as db:
        source = Source(name='synthetic', url='https://example.org', language='en')
        db.add(source); db.flush()
        item = IntakeItem(source_id=source.id, fingerprint='1', url='https://example.org/1', text='synthetic', published_at=NOW, collected_at=NOW-timedelta(days=days), raw_digest='a'*64)
        db.add(item); db.commit()
    return engine


def asset(db, root, **kwargs):
    root.mkdir(exist_ok=True)
    path = root/'synthetic.bin'; path.write_bytes(b'synthetic')
    values = dict(item_id=1,local_path=str(path),mime_type='image/png',byte_size=9,sha256='b'*64,collected_at=NOW-timedelta(days=31),expires_at=NOW+timedelta(days=99))
    values.update(kwargs)
    row = MediaAsset(**values); db.add(row); db.commit(); return row.id


def test_media_cap_missing_recovery_dryrun_and_failure(tmp_path):
    engine = seed(tmp_path); root = tmp_path/'media'
    with Session(engine) as db: asset(db,root)
    before = (tmp_path/'synthetic.db').read_bytes()
    result = run_retention(engine,root,NOW)
    assert result['media'] == result['intake'] == 1
    assert (tmp_path/'synthetic.db').read_bytes() == before
    assert (root/'synthetic.bin').exists()
    (root/'synthetic.bin').unlink()
    assert run_retention(engine,root,NOW,apply=True)['intake'] == 1
    with Session(engine) as db:
        assert db.scalar(select(Audit).where(Audit.action=='media.deleted'))
        assert db.scalar(select(RetentionRun))


@pytest.mark.parametrize('protection',['incident','promoted','evidence','preview','child_hold','intake_hold','recent_revision','recent_media'])
def test_protections(tmp_path,protection):
    engine = seed(tmp_path); root=tmp_path/'media'
    with Session(engine) as db:
        item=db.get(IntakeItem,1)
        if protection=='incident':
            incident=Incident(fields={});db.add(incident);db.flush();item.incident_id=incident.id
        elif protection=='promoted': item.status='promoted'
        elif protection=='evidence':
            incident=Incident(fields={});db.add(incident);db.flush()
            db.add(Evidence(incident_id=incident.id,source_id=item.source_id,url=item.url,text='synthetic',published_at='',digest='a'*64))
        elif protection=='preview':
            db.add(TelegramPublicationPreview(item_id=1,draft_hash='c'*64,source_digest='a'*64,record={},safety={},created_at=NOW,expires_at=NOW+timedelta(seconds=1)))
        elif protection=='recent_revision': db.add(IntakeRevision(item_id=1,text='synthetic',raw_digest='c'*64,collected_at=NOW))
        db.commit()
        if protection=='recent_media': asset(db,root,collected_at=NOW,expires_at=NOW+timedelta(days=30))
        elif protection not in ('recent_revision',): asset(db,root)
    if protection=='intake_hold': place_hold(engine,'intake',1,'preserve',NOW)
    if protection=='child_hold': place_hold(engine,'media',1,'preserve',NOW)
    result=run_retention(engine,root,NOW,apply=True)
    assert result['intake']==0
    with Session(engine) as db: assert db.get(IntakeItem,1)
    if protection not in ('recent_revision','recent_media'):
        assert (root/'synthetic.bin').exists()


@pytest.mark.parametrize('kind',['symlink','ancestor','hardlink','outside','extension','traversal','directory'])
def test_unsafe_files(tmp_path,kind):
    root=tmp_path/'media';root.mkdir();path=root/'safe.bin';path.write_bytes(b'synthetic')
    outside=tmp_path/'outside.bin';outside.write_bytes(b'preserve')
    if kind=='symlink': path.unlink();path.symlink_to(outside)
    if kind=='ancestor':
        moved=tmp_path/'moved';root.rename(moved);root.symlink_to(moved,target_is_directory=True)
    if kind=='hardlink': os.link(path,root/'link.bin')
    if kind=='outside': path=outside
    if kind=='extension': path= root/'unsafe.txt';path.write_bytes(b'x')
    if kind=='traversal': path=root/'..'/'outside.bin'
    if kind=='directory': path.unlink();path.mkdir()
    with pytest.raises((RetentionError,OSError)): safe_file(path,root,unlink=True)
    assert outside.read_bytes()==b'preserve'


def test_naive_time_and_no_root_creation(tmp_path):
    engine=seed(tmp_path)
    with pytest.raises(RetentionError): run_retention(engine,tmp_path,NOW.replace(tzinfo=None))
    missing=tmp_path/'missing'
    run_retention(engine,missing,NOW)
    assert not missing.exists()


def test_unlink_failure_keeps_parent_then_retries(tmp_path,monkeypatch):
    engine=seed(tmp_path);root=tmp_path/'media'
    with Session(engine) as db: asset(db,root)
    unlink=os.unlink
    def failed(*args,**kwargs): raise PermissionError('PRIVATE SECRET PATH')
    monkeypatch.setattr(os,'unlink',failed)
    result=run_retention(engine,root,NOW,apply=True)
    assert result['failed']==1 and result['intake']==0
    monkeypatch.setattr(os,'unlink',unlink)
    assert run_retention(engine,root,NOW,apply=True)['intake']==1


def test_bounded_quarantine(tmp_path):
    engine=seed(tmp_path,days=0)
    with Session(engine) as db:
        db.add_all([IntakeQuarantine(source_id=1,reason='synthetic',raw_digest=str(i),created_at=NOW-timedelta(days=181)) for i in range(1001)])
        db.commit()
    result=run_retention(engine,tmp_path,NOW,apply=True)
    assert result['quarantine']==1000 and result['bounded']==1
    assert run_retention(engine,tmp_path,NOW,apply=True)['quarantine']==1

from fastapi.testclient import TestClient
from syosint.api import create_app
from syosint.retention_cli import run_cli


def test_strict_api_gates_holds_safe_errors(tmp_path,monkeypatch):
    engine=seed(tmp_path)
    monkeypatch.setenv('SYOSINT_PRIVATE_DIR',str(tmp_path))
    client=TestClient(create_app(f"sqlite:///{tmp_path/'synthetic.db'}",tmp_path/'exports'),base_url='http://127.0.0.1:8765')
    assert client.get('/retention/status').json()['last_run'] is None
    assert client.post('/retention/preview').json()['intake']==1
    assert client.post('/retention/run',json={'acknowledged':True}).status_code==403
    for payload in ({'target_kind':'bad','target_id':1,'reason':'x'},{'target_kind':'intake','target_id':True,'reason':'x'},{'target_kind':'intake','target_id':1,'reason':'x','extra':'x'}):
        assert client.post('/retention/holds',json=payload).status_code==422
    payload={'target_kind':'intake','target_id':1,'reason':' preserve '}
    response=client.post('/retention/holds',json=payload)
    assert response.status_code==200, response.text
    hold=response.json(); assert hold['reason']=='preserve'
    assert client.post('/retention/holds',json=payload).status_code==409
    assert client.get('/retention/holds').json()==[hold]
    assert client.post('/retention/preview').json()['intake']==0
    assert client.post(f"/retention/holds/{hold['id']}/release",json={'reason':'done'}).status_code==200
    assert client.post(f"/retention/holds/{hold['id']}/release",json={'reason':'done'}).status_code==409
    assert client.post('/retention/holds',json={**payload,'target_id':999}).status_code==400
    monkeypatch.setattr('syosint.retention.run_retention',lambda *a,**k: (_ for _ in ()).throw(OSError('SECRET PRIVATE PATH')))
    assert client.post('/retention/preview').json()=={'detail':'Retention unavailable'}


def test_apply_api_and_cli_no_missing_database_creation(tmp_path,monkeypatch,capsys):
    missing=tmp_path/'absent.db'
    monkeypatch.setenv('SYOSINT_DB_PATH',str(missing))
    assert run_cli(['preview'])==2
    assert not missing.exists()
    seed(tmp_path)
    monkeypatch.setenv('SYOSINT_DB_PATH',str(tmp_path/'synthetic.db'))
    monkeypatch.setenv('SYOSINT_PRIVATE_DIR',str(tmp_path))
    assert run_cli(['preview'])==0
    assert run_cli(['run','--apply'])==2
    monkeypatch.setenv('SYOSINT_RETENTION_APPLY','1')
    client=TestClient(create_app(f"sqlite:///{tmp_path/'synthetic.db'}",tmp_path/'exports'),base_url='http://127.0.0.1:8765')
    assert client.post('/retention/run',json={'acknowledged':False}).status_code==403
    assert client.post('/retention/run',json={'acknowledged':True,'extra':1}).status_code==422
    assert client.post('/retention/run',json={'acknowledged':True}).json()['intake']==1
    assert client.get('/retention/status').json()['last_run']['status']=='complete'


@pytest.mark.asyncio
async def test_scheduler_failure_recovery_and_shutdown(tmp_path,monkeypatch):
    import asyncio
    from syosint.retention_scheduler import RetentionScheduler
    engine=seed(tmp_path); calls=[]
    def run(*a,**kw):
        calls.append(kw['apply'])
        if len(calls)==1: raise OSError('secret')
        return {}
    monkeypatch.setattr('syosint.retention_scheduler.run_retention',run)
    scheduler=RetentionScheduler(engine,tmp_path,tick_seconds=.001)
    scheduler._running=True
    assert await scheduler.run_once() is None
    scheduler._running=False
    scheduler.start()
    for _ in range(100):
        if len(calls)>=2: break
        await asyncio.sleep(.001)
    await scheduler.stop()
    assert len(calls)>=2 and calls==[False]*len(calls)
    assert scheduler._task.done()


def test_rehold_preserves_released_history(tmp_path):
    from syosint.models import RetentionHold
    engine=seed(tmp_path)
    first=place_hold(engine,'intake',1,'first',NOW)
    release_hold(engine,first['id'],'released',NOW)
    second=place_hold(engine,'intake',1,'second',NOW)
    assert second['id']!=first['id']
    with Session(engine) as db:
        old=db.get(RetentionHold,first['id'])
        assert old.reason=='first' and old.released_at is not None


def test_descriptor_keeps_original_directory_during_ancestor_swap(tmp_path,monkeypatch):
    root=tmp_path/'media';root.mkdir();(root/'safe.bin').write_bytes(b'synthetic')
    outside=tmp_path/'outside';outside.mkdir();(outside/'safe.bin').write_bytes(b'preserve')
    moved=tmp_path/'original'
    original_stat=os.stat; swapped=False
    def swap(path,*args,**kwargs):
        nonlocal swapped
        result=original_stat(path,*args,**kwargs)
        if path=='safe.bin' and kwargs.get('dir_fd') is not None and not swapped:
            swapped=True
            root.rename(moved);root.symlink_to(outside,target_is_directory=True)
        return result
    monkeypatch.setattr(os,'stat',swap)
    safe_file(root/'safe.bin',root,unlink=True)
    assert (outside/'safe.bin').read_bytes()==b'preserve'
    assert not (moved/'safe.bin').exists()


def test_hold_waits_for_apply_write_lock_and_cannot_target_deleted_row(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    import threading
    from sqlalchemy import text
    engine=seed(tmp_path)
    started=threading.Event()
    def hold():
        started.set()
        return place_hold(engine,'intake',1,'preserve',NOW)
    with Session(engine) as db, ThreadPoolExecutor(max_workers=1) as workers:
        db.execute(text('BEGIN IMMEDIATE'))
        future=workers.submit(hold)
        assert started.wait(1)
        assert not future.done()
        db.delete(db.get(IntakeItem,1));db.commit()
        with pytest.raises(RetentionError): future.result(timeout=3)


@pytest.mark.asyncio
async def test_lifespan_scheduler_default_preview(tmp_path,monkeypatch):
    monkeypatch.setenv('SYOSINT_RSS_SCHEDULER','0')
    monkeypatch.setenv('SYOSINT_TELEGRAM_SCHEDULER','0')
    monkeypatch.delenv('SYOSINT_RETENTION_SCHEDULER',raising=False)
    monkeypatch.delenv('SYOSINT_RETENTION_APPLY',raising=False)
    seed(tmp_path)
    app=create_app(f"sqlite:///{tmp_path/'synthetic.db'}",tmp_path/'exports')
    async with app.router.lifespan_context(app):
        import asyncio
        await asyncio.sleep(0)
        assert app.state.retention_scheduler.apply is False
    assert app.state.retention_scheduler._task.done()
    with Session(app.state.engine) as db:
        assert db.get(IntakeItem,1)
        assert db.scalar(select(RetentionRun)) is None


def test_protected_prefix_does_not_starve_eligible_quarantine(tmp_path):
    from syosint.models import RetentionHold
    engine=seed(tmp_path,days=0)
    with Session(engine) as db:
        db.add_all([IntakeQuarantine(source_id=1,reason='synthetic',raw_digest=str(i),created_at=NOW-timedelta(days=181)) for i in range(1002)])
        db.flush()
        db.add_all([RetentionHold(target_kind='quarantine',target_id=i,reason='preserve',created_at=NOW) for i in range(1,1002)])
        db.commit()
    result=run_retention(engine,tmp_path,NOW,apply=True)
    assert result['quarantine']==1
    with Session(engine) as db:
        assert db.get(IntakeQuarantine,1001)
        assert db.get(IntakeQuarantine,1002) is None


def test_populated_0007_migration_preserves_history(tmp_path):
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from sqlalchemy import create_engine, text
    path=tmp_path/'migration.db'
    config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    config.set_main_option('sqlalchemy.url',f'sqlite:///{path}')
    command.upgrade(config,'0007')
    engine=create_engine(f'sqlite:///{path}')
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO audit (timestamp,action,entity,entity_id,reason) VALUES ('2026-01-01','synthetic','source',1,'preserve')"))
    command.upgrade(config,'head')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT version_num FROM alembic_version'))=='0008'
        assert conn.scalar(text('SELECT reason FROM audit'))=='preserve'
        assert conn.scalar(text('SELECT count(*) FROM retention_holds'))==0


def test_recent_media_prefix_does_not_starve_eligible_metadata(tmp_path):
    engine=seed(tmp_path)
    with Session(engine) as db:
        db.add_all([IntakeItem(source_id=1,fingerprint=str(i),url=f'https://example.org/{i}',text='synthetic',published_at=NOW,collected_at=NOW-timedelta(days=181),raw_digest='a'*64) for i in range(2,1002)])
        db.flush()
        db.add_all([MediaAsset(item_id=i,local_path=str(tmp_path/f'{i}.bin'),mime_type='image/png',byte_size=1,sha256='b'*64,collected_at=NOW,expires_at=NOW+timedelta(days=30)) for i in range(1,1001)])
        db.commit()
    assert run_retention(engine,tmp_path,NOW)['intake']==1
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake']==1
    with Session(engine) as db:
        assert db.get(IntakeItem,1)
        assert db.get(IntakeItem,1001) is None


def test_public_publication_history_survives_retention(tmp_path):
    from syosint.models import TelegramPublication, TelegramPublicationRevision
    engine=seed(tmp_path)
    with Session(engine) as db:
        pub=TelegramPublication(item_id=1,public_id='synthetic',source_digest='a'*64,record={},status='withdrawn',approved_at=NOW)
        db.add(pub);db.flush()
        db.add(TelegramPublicationRevision(publication_id=pub.id,action='withdrawn',reason_en='synthetic',reason_ar='synthetic',revised_at=NOW))
        db.commit()
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake']==0
    with Session(engine) as db:
        assert db.scalar(select(TelegramPublication))
        assert db.scalar(select(TelegramPublicationRevision))


def test_large_revision_family_drains_in_bounded_steps(tmp_path):
    engine=seed(tmp_path)
    with Session(engine) as db:
        db.add_all([IntakeRevision(item_id=1,text='synthetic',raw_digest='c'*64,collected_at=NOW-timedelta(days=181)) for _ in range(1001)])
        db.commit()
    preview=run_retention(engine,tmp_path,NOW)
    assert preview['intake']==0 and preview['bounded'] is True
    result=run_retention(engine,tmp_path,NOW,apply=True)
    assert result['intake']==0 and result['bounded'] is True
    with Session(engine) as db:
        assert len(list(db.scalars(select(IntakeRevision))))==1
        assert db.get(IntakeItem,1)
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake']==1


def test_deleted_intake_id_is_never_reused_by_new_target(tmp_path):
    from syosint.models import RetentionHold
    engine=seed(tmp_path)
    first=place_hold(engine,'intake',1,'original target',NOW)
    release_hold(engine,first['id'],'done',NOW)
    assert run_retention(engine,tmp_path,NOW,apply=True)['intake']==1
    with Session(engine) as db:
        row=IntakeItem(source_id=1,fingerprint='new',url='https://example.org/new',text='synthetic',published_at=NOW,collected_at=NOW,raw_digest='c'*64)
        db.add(row);db.commit()
        assert row.id>1
        assert db.get(RetentionHold,first['id']).target_id==1
