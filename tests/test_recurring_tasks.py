from datetime import date
from tests.conftest import login
from app.models import Task
from app.extensions import db

def test_create_recurring_tasks(client, student):
    login(client)

    # Valid daily task
    resp = client.post('/api/tasks', json={'title': 'Daily Standup', 'recurrence': 'daily', 'due_date': '2026-10-15'})
    assert resp.status_code == 201
    assert resp.get_json()['data']['recurrence'] == 'daily'

    # Valid weekly task
    resp = client.post('/api/tasks', json={'title': 'Weekly Review', 'recurrence': 'weekly'})
    assert resp.status_code == 201
    assert resp.get_json()['data']['recurrence'] == 'weekly'

    # Valid monthly task
    resp = client.post('/api/tasks', json={'title': 'Monthly Report', 'recurrence': 'monthly'})
    assert resp.status_code == 201
    assert resp.get_json()['data']['recurrence'] == 'monthly'

    # Invalid recurrence
    resp = client.post('/api/tasks', json={'title': 'Invalid', 'recurrence': 'yearly'})
    assert resp.status_code == 400
    assert 'recurrence' in resp.get_json()['error']

def test_daily_recurring_task_completion(client, student, app):
    login(client)
    resp = client.post('/api/tasks', json={'title': 'Daily Habit', 'recurrence': 'daily', 'due_date': '2026-10-15'})
    task_id = resp.get_json()['data']['id']

    # Mark completed
    resp = client.put(f'/api/tasks/{task_id}', json={'completed': True})
    assert resp.status_code == 200
    assert resp.get_json()['data']['completed'] is True

    # Check tasks: should have 2 tasks now (original completed, new pending due 2026-10-16)
    tasks_resp = client.get('/api/tasks')
    tasks = tasks_resp.get_json()['data']
    assert len(tasks) == 2

    completed_task = next(t for t in tasks if t['id'] == task_id)
    assert completed_task['completed'] is True

    next_task = next(t for t in tasks if t['id'] != task_id)
    assert next_task['title'] == 'Daily Habit'
    assert next_task['completed'] is False
    assert next_task['recurrence'] == 'daily'
    assert next_task['due_date'] == '2026-10-16'

def test_weekly_recurring_task_completion(client, student, app):
    login(client)
    resp = client.post('/api/tasks', json={'title': 'Weekly Clean', 'recurrence': 'weekly', 'due_date': '2026-10-10'})
    task_id = resp.get_json()['data']['id']

    # Mark completed
    client.put(f'/api/tasks/{task_id}', json={'completed': True})

    tasks = client.get('/api/tasks').get_json()['data']
    assert len(tasks) == 2
    next_task = next(t for t in tasks if t['id'] != task_id)
    assert next_task['due_date'] == '2026-10-17'
    assert next_task['completed'] is False

def test_monthly_recurring_task_completion(client, student, app):
    login(client)
    # January 31 should advance to February 28
    resp = client.post('/api/tasks', json={'title': 'Monthly Bills', 'recurrence': 'monthly', 'due_date': '2026-01-31'})
    task_id = resp.get_json()['data']['id']

    client.put(f'/api/tasks/{task_id}', json={'completed': True})

    tasks = client.get('/api/tasks').get_json()['data']
    next_task = next(t for t in tasks if t['id'] != task_id)
    assert next_task['due_date'] == '2026-02-28'
    assert next_task['completed'] is False

def test_non_recurring_task_completion_does_not_duplicate(client, student):
    login(client)
    resp = client.post('/api/tasks', json={'title': 'One-off Task', 'recurrence': 'none', 'due_date': '2026-10-20'})
    task_id = resp.get_json()['data']['id']

    client.put(f'/api/tasks/{task_id}', json={'completed': True})

    tasks = client.get('/api/tasks').get_json()['data']
    assert len(tasks) == 1
    assert tasks[0]['completed'] is True

def test_uncompleting_task_does_not_spawn(client, student):
    login(client)
    resp = client.post('/api/tasks', json={'title': 'Daily Habit', 'recurrence': 'daily', 'due_date': '2026-10-15'})
    task_id = resp.get_json()['data']['id']

    # Complete once (creates 2nd task)
    client.put(f'/api/tasks/{task_id}', json={'completed': True})
    assert len(client.get('/api/tasks').get_json()['data']) == 2

    # Uncomplete original task
    client.put(f'/api/tasks/{task_id}', json={'completed': False})
    assert len(client.get('/api/tasks').get_json()['data']) == 2
