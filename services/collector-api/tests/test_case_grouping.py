import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from syosint.api import create_app

EDIT = dict(title_en='Synthetic outage', title_ar='انقطاع تجريبي', category='infrastructure',
            summary_en='Synthetic report', summary_ar='تقرير تجريبي', uncertainty_en='Unknown',
            uncertainty_ar='غير مؤكد', location_en='Withheld', location_ar='محجوب',
            precision='withheld', occurred_at='2026-10-12T10:00:00Z', confidence='unverified')


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(f"sqlite:///{tmp_path / 'vault.sqlite'}", tmp_path / 'exports'),
                      base_url='http://127.0.0.1:8765')


def case(client, **changes):
    case_id = client.post('/incidents', json={key: EDIT[key] for key in ('title_en', 'title_ar', 'category')}).json()['id']
    response = client.put(f'/incidents/{case_id}', json={**EDIT, 'private_governorate': 'aleppo', **changes})
    assert response.status_code == 200, response.text
    return case_id


def test_matching_boundary_offsets_and_no_side_effects(client, tmp_path):
    current = case(client)
    near = case(client, occurred_at='2026-10-12T12:00:00+02:00')
    edge = case(client, occurred_at='2026-10-12T16:00:00Z')
    case(client, occurred_at='2026-10-12T16:00:01Z')
    case(client, private_governorate='homs')
    case(client, category='humanitarian')
    before = client.get('/incidents').json(), client.get('/audit').json()
    response = client.get(f'/incidents/{current}/related')
    assert response.status_code == 200
    matches = response.json()
    assert [match['id'] for match in matches] == [near, edge]
    assert [match['time_difference_seconds'] for match in matches] == [0, 21600]
    assert matches[0]['occurred_at'] == '2026-10-12T10:00:00Z'
    assert set(matches[0]) == {'id', 'state', 'title_en', 'title_ar', 'occurred_at', 'private_governorate', 'time_difference_seconds'}
    assert client.get(f'/incidents/{current}/related').json() == matches
    assert before == (client.get('/incidents').json(), client.get('/audit').json())
    assert not (tmp_path / 'exports').exists()


def test_missing_invalid_historical_metadata_and_withdrawal_fail_closed(client, tmp_path):
    current = case(client)
    ids = [case(client) for _ in range(4)]
    with sqlite3.connect(tmp_path / 'vault.sqlite') as db:
        for case_id, timestamp in zip(ids[:3], ['not-a-time', '2026-10-12T10:00:00', None]):
            fields = {**EDIT, 'private_governorate': 'aleppo', 'occurred_at': timestamp}
            db.execute('update incidents set fields=? where id=?', (json.dumps(fields), case_id))
        db.execute("update incidents set state='withdrawn' where id=?", (ids[3],))
    assert client.get(f'/incidents/{current}/related').json() == []
    incomplete = case(client, private_governorate=None)
    assert client.get(f'/incidents/{incomplete}/related').json() == []
    assert client.get('/incidents/9999/related').status_code == 404


def test_limit_and_order(client):
    current = case(client)
    ids = [case(client) for _ in range(12)]
    assert [match['id'] for match in client.get(f'/incidents/{current}/related').json()] == ids[:10]


def test_private_governorate_validation_and_clear(client):
    case_id = case(client)
    assert client.put(f'/incidents/{case_id}', json={**EDIT, 'private_governorate': 'invalid'}).status_code == 422
    assert client.put(f'/incidents/{case_id}', json=EDIT).status_code == 200
    assert 'private_governorate' not in client.get(f'/incidents/{case_id}').json()


def test_private_facet_never_enters_public_preview(client):
    case_id = case(client)
    source_id = client.post('/sources', json=dict(name='Synthetic source', url='https://example.org', language='en')).json()['id']
    assert client.post(f'/incidents/{case_id}/evidence', json=dict(source_id=source_id, url='https://example.org/report', text='Synthetic evidence', published_at=EDIT['occurred_at'])).status_code == 201
    for state in ['investigating', 'review-ready']:
        assert client.post(f'/incidents/{case_id}/transition', json=dict(state=state, reason='Synthetic review')).status_code == 200
    checks = {key: True for key in ['independence_checked', 'time_checked', 'location_checked', 'contradictions_checked', 'person_safety_checked', 'operational_safety_checked', 'contradictions_acknowledged', 'human_approved']}
    assert client.post(f'/incidents/{case_id}/review', json=dict(rationale='Synthetic test rationale', **checks)).status_code == 200
    assert client.post(f'/incidents/{case_id}/transition', json=dict(state='approved', reason='Synthetic approval')).status_code == 200
    preview = client.get(f'/incidents/{case_id}/preview')
    assert preview.status_code == 200
    assert 'private_governorate' not in preview.text and 'aleppo' not in preview.text


@pytest.mark.parametrize('field,value', [('private_governorate', []), ('private_governorate', {}), ('category', [])])
def test_invalid_historical_facet_types_fail_closed(client, tmp_path, field, value):
    case_id = case(client)
    with sqlite3.connect(tmp_path / 'vault.sqlite') as db:
        db.execute('update incidents set fields=? where id=?', (json.dumps({**EDIT, 'private_governorate': 'aleppo', field: value}), case_id))
    response = client.get(f'/incidents/{case_id}/related')
    assert response.status_code == 200
    assert response.json() == []
