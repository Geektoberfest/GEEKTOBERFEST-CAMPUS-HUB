import json
from tests.conftest import login

def test_task_crud_and_ownership(client,student,app):
    login(client)
    r=client.post('/api/tasks',json={'title':'Study Flask','priority':'high','category':'exam','due_date':'2030-01-01'}); assert r.status_code==201; task=r.get_json()['data']; tid=task['id']
    assert client.get('/api/tasks').status_code==200
    assert client.put(f'/api/tasks/{tid}',json={'completed':True}).status_code==200
    assert client.delete(f'/api/tasks/{tid}').status_code==200

def test_protected_task_api(client):
    assert client.get('/api/tasks').status_code==401

def test_task_page_and_copy_details(client,student):
    login(client)
    res = client.get('/tasks')
    assert res.status_code == 200
    assert b'tasks.js' in res.data
    js_res = client.get('/static/js/tasks.js')
    assert js_res.status_code == 200
    assert b'copyTaskDetails' in js_res.data
    assert b'Copy task details' in js_res.data

# ── Bulk action tests ─────────────────────────────────────────────────────────

def _create_task(client, title='Task', **kwargs):
    payload = {'title': title, 'priority': 'medium', 'category': 'other', **kwargs}
    r = client.post('/api/tasks', json=payload)
    assert r.status_code == 201
    return r.get_json()['data']['id']

def test_bulk_complete_all(client, student):
    login(client)
    ids = [_create_task(client, f'Task {i}') for i in range(3)]
    r = client.post('/api/tasks/bulk', json={'action': 'complete_all', 'ids': ids})
    assert r.status_code == 200
    data = r.get_json()['data']
    assert data['affected'] == 3
    tasks = client.get('/api/tasks?status=completed').get_json()['data']
    completed_ids = {t['id'] for t in tasks}
    assert set(ids) <= completed_ids

def test_bulk_incomplete_all(client, student):
    login(client)
    ids = [_create_task(client, f'Task {i}') for i in range(2)]
    client.post('/api/tasks/bulk', json={'action': 'complete_all', 'ids': ids})
    r = client.post('/api/tasks/bulk', json={'action': 'incomplete_all', 'ids': ids})
    assert r.status_code == 200
    assert r.get_json()['data']['affected'] == 2
    tasks = client.get('/api/tasks?status=pending').get_json()['data']
    pending_ids = {t['id'] for t in tasks}
    assert set(ids) <= pending_ids

def test_bulk_delete_all(client, student):
    login(client)
    ids = [_create_task(client, f'Task {i}') for i in range(4)]
    r = client.post('/api/tasks/bulk', json={'action': 'delete_all', 'ids': ids})
    assert r.status_code == 200
    assert r.get_json()['data']['affected'] == 4
    remaining = client.get('/api/tasks').get_json()['data']
    remaining_ids = {t['id'] for t in remaining}
    assert not set(ids) & remaining_ids

def test_bulk_invalid_action(client, student):
    login(client)
    tid = _create_task(client)
    r = client.post('/api/tasks/bulk', json={'action': 'fly_away', 'ids': [tid]})
    assert r.status_code == 400

def test_bulk_empty_ids(client, student):
    login(client)
    r = client.post('/api/tasks/bulk', json={'action': 'complete_all', 'ids': []})
    assert r.status_code == 400

def test_bulk_ownership_isolation(client, student, admin, app):
    """Bulk action cannot affect another user's tasks."""
    login(client)
    tid = _create_task(client, 'My task')
    # Log in as admin
    client.post('/api/auth/logout')
    client.post('/login', data={'email': 'admin@test.local', 'password': 'Password123'}, follow_redirects=True)
    r = client.post('/api/tasks/bulk', json={'action': 'delete_all', 'ids': [tid]})
    # Either 404 (task not found for this user) or affected==0
    body = r.get_json()
    assert r.status_code == 404 or body.get('data', {}).get('affected', 0) == 0

def test_bulk_protected(client):
    r = client.post('/api/tasks/bulk', json={'action': 'complete_all', 'ids': [1]})
    assert r.status_code == 401
