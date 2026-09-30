"""Behavioral coverage for inert, durable candidate review."""
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from syosint.api import create_app

CHECKS = {key: True for key in (
    'accessibility_checked', 'relevance_checked', 'identity_checked',
    'provenance_checked', 'policy_checked',
)}
PAYLOAD = dict(platform='web', url='https://EXAMPLE.org/', name='Private lead',
               language='en', suggestion_reason='Potential Syria reporting')

@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / 'exports'),
                      base_url='http://127.0.0.1:8765')


def submit(client, **changes):
    response = client.post('/candidates', json={**PAYLOAD, **changes})
    assert response.status_code == 201
    return response.json()


def test_create_list_detail_restart_and_private_audit(client, tmp_path):
    candidate = submit(client)
    assert candidate['canonical_url'] == 'https://example.org'
    assert candidate['status'] == 'pending'
    assert candidate['created_at'] and candidate['updated_at']
    assert client.get('/candidates').json() == [candidate]
    assert client.get(f"/candidates/{candidate['id']}").json() == {**candidate, 'reviews': []}
    with sqlite3.connect(tmp_path / 'vault.sqlite') as db:
        assert db.execute('select version_num from alembic_version').fetchone() == ('0006',)
    restarted = TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / 'exports'), base_url='http://127.0.0.1:8765')
    assert restarted.get('/candidates').json() == [candidate]
    audit = restarted.get('/audit').json()
    assert [row['action'] for row in audit] == ['candidate.created']
    assert 'Private lead' not in str(audit) and 'Potential Syria reporting' not in str(audit)
    assert client.get('/sources').json() == []
    assert not (tmp_path / 'exports').exists()


def test_duplicate_and_registered_source_conflicts(client):
    candidate = submit(client)
    duplicate = client.post('/candidates', json={**PAYLOAD, 'url': 'https://example.org'})
    assert duplicate.status_code == 409
    assert duplicate.json()['detail'] == {'kind': 'candidate', 'id': candidate['id']}
    source = client.post('/sources', json=dict(name='Existing', url='https://OTHER.example/', language='en')).json()
    conflict = client.post('/candidates', json={**PAYLOAD, 'url': 'https://other.example'})
    assert conflict.status_code == 409
    assert conflict.json()['detail'] == {'kind': 'source', 'id': source['id']}
    assert len(client.get('/candidates').json()) == 1


@pytest.mark.parametrize('url', ['http://example.org', 'https://localhost', 'https://foo.local',
    'https://foo.localhost', 'https://foo.internal', 'https://127.0.0.1', 'https://[::1]',
    'https://' + 'user:' + 'pass@' + 'example.org',
    'https://example.org/#fragment', 'https://example.org:bad',
    'https://example.org:444', 'https://example.org\\@localhost', 'https://example.org/\nprivate'])
def test_unsafe_urls_are_refused(client, url):
    assert client.post('/candidates', json={**PAYLOAD, 'url': url}).status_code == 422


@pytest.mark.parametrize('url', ['https://t.me/+invite', 'https://t.me/channel_name/123',
    'https://example.org/channel_name', 'https://t.me/c/123', 'https://t.me/channel_name?start=x'])
def test_non_public_username_telegram_links_are_refused(client, url):
    assert client.post('/candidates', json={**PAYLOAD, 'platform': 'telegram', 'url': url}).status_code == 422


def test_telegram_username_and_web_path_normalization(client):
    assert submit(client, platform='telegram', url='https://T.ME/Channel_Name')['canonical_url'] == 'https://t.me/channel_name'
    assert submit(client, url='https://EXAMPLE.org/News/?q=AbC')['canonical_url'] == 'https://example.org/News/?q=AbC'


@pytest.mark.parametrize('changes', [dict(name=' '), dict(name='x'*251), dict(suggestion_reason=''),
    dict(suggestion_reason='x'*1001), dict(language='fr'), dict(platform='rss'), dict(extra='private')])
def test_strict_bounded_create_input(client, changes):
    assert client.post('/candidates', json={**PAYLOAD, **changes}).status_code == 422


def test_review_gates_history_and_no_activation(client, tmp_path):
    candidate = submit(client)
    route = f"/candidates/{candidate['id']}/reviews"
    for key in CHECKS:
        assert client.post(route, json=dict(decision='accepted', reason='Suitable', checks={**CHECKS, key: False})).status_code == 422
    for checks in ({}, {**CHECKS, 'extra': True}, {**CHECKS, 'policy_checked': 'true'}):
        assert client.post(route, json=dict(decision='accepted', reason='Suitable', checks=checks)).status_code == 422
    for reason in ('', ' ', 'x'*1001):
        assert client.post(route, json=dict(decision='accepted', reason=reason, checks=CHECKS)).status_code == 422
    rejected_checks = {**CHECKS, 'identity_checked': False}
    rejection = client.post(route, json=dict(decision='rejected', reason='Identity not established', checks=rejected_checks))
    assert rejection.status_code == 201
    acceptance = client.post(route, json=dict(decision='accepted', reason='Identity now established', checks=CHECKS))
    assert acceptance.status_code == 201
    detail = client.get(f"/candidates/{candidate['id']}").json()
    assert detail['status'] == 'accepted'
    assert detail['reviews'] == [rejection.json(), acceptance.json()]
    assert detail['reviews'][0]['checks'] == rejected_checks
    assert all(event['created_at'] for event in detail['reviews'])
    assert detail['reviews'][0]['id'] < detail['reviews'][1]['id']
    restarted = TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / 'exports'), base_url='http://127.0.0.1:8765')
    assert restarted.get(f"/candidates/{candidate['id']}").json() == detail
    assert client.get('/sources').json() == []
    assert not (tmp_path / 'exports').exists()
    audit = client.get('/audit').json()
    assert [row['action'] for row in audit] == ['candidate.created', 'candidate.reviewed', 'candidate.reviewed']
    assert 'Identity not established' not in str(audit)


def test_unknown_ids_and_bounded_filtered_list(client):
    assert client.get('/candidates/999').status_code == 404
    assert client.post('/candidates/999/reviews', json=dict(decision='rejected', reason='Unknown', checks=CHECKS)).status_code == 404
    first = submit(client)
    second = submit(client, url='https://second.example')
    client.post(f"/candidates/{first['id']}/reviews", json=dict(decision='rejected', reason='Not relevant', checks=CHECKS))
    assert [row['id'] for row in client.get('/candidates').json()] == [second['id'], first['id']]
    assert [row['id'] for row in client.get('/candidates?status=rejected').json()] == [first['id']]
    assert [row['id'] for row in client.get('/candidates?status=pending').json()] == [second['id']]
    assert client.get('/candidates?status=accepted').json() == []
    assert [row['id'] for row in client.get('/candidates?limit=1&offset=1').json()] == [first['id']]
    assert client.get('/candidates?limit=100').status_code == 200
    for query in ('status=all', 'limit=101', 'limit=0', 'offset=-1'):
        assert client.get('/candidates?' + query).status_code == 422


def test_database_unique_constraint_guards_second_session(client):
    candidate = submit(client)
    from syosint.models import SourceCandidate
    with Session(client.app.state.engine) as second:
        second.add(SourceCandidate(platform='web', canonical_url='https://example.org', name='Race',
                                   language='en', suggestion_reason='Concurrent lead'))
        with pytest.raises(IntegrityError):
            second.commit()
        second.rollback()
        assert second.scalar(select(func.count()).select_from(SourceCandidate)) == 1
    assert client.get(f"/candidates/{candidate['id']}").status_code == 200


@pytest.mark.parametrize('url', [
    'https://127.0.0.1./', 'https://127.1/', 'https://2130706433/',
    'https://0177.0.0.1/', 'https://0x7f.0x0.0x0.0x1/',
    'https://bad_host.example/', 'https://-bad.example/', 'https://bad..example/',
])
def test_numeric_ip_variants_and_invalid_dns_hosts_are_refused(client, url):
    assert client.post('/candidates', json={**PAYLOAD, 'url': url}).status_code == 422


@pytest.mark.parametrize('url', [
    'https://t.me/+invite', 'https://t.me/channel_name/123',
    'https://t.me/channel_name', 'https://T.ME./channel_name',
])
def test_web_platform_cannot_bypass_telegram_link_policy(client, url):
    assert client.post('/candidates', json={**PAYLOAD, 'url': url}).status_code == 422


@pytest.mark.parametrize('url', [
    'https://foo.bar。local', 'https://foo.bar。localhost', 'https://foo.bar。internal',
    'https://foo.ｌｏｃａｌ', 'https://foo.ｌｏｃａｌｈｏｓｔ', 'https://foo.ｉｎｔｅｒｎａｌ',
])
def test_idna_local_hostname_variants_are_refused(client, url):
    assert client.post('/candidates', json={**PAYLOAD, 'url': url}).status_code == 422
