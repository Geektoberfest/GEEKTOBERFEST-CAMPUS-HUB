from datetime import date, timedelta
from tests.conftest import login
from app.extensions import db
from app.models import User, Task, StudySession
from app.services.study_planner import generate_study_schedule, save_study_schedule


def create_user(app, name, email):
    with app.app_context():
        u = User(name=name, email=email, role='student')
        u.set_password('Password123')
        db.session.add(u)
        db.session.commit()
        return u.id


def test_generate_schedule_empty(app, student):
    with app.app_context():
        user = db.session.get(User, student)
        plan = generate_study_schedule(user, daily_hours=2.0, days_ahead=7)
        assert plan['summary']['total_planned_hours'] == 0
        assert plan['summary']['total_tasks_scheduled'] == 0
        assert len(plan['days']) == 0


def test_generate_schedule_with_tasks(app, student):
    today = date.today()
    with app.app_context():
        user = db.session.get(User, student)
        t_high = Task(user_id=user.id, title='Exam Prep', priority='high', category='exam', due_date=today + timedelta(days=2))
        t_low = Task(user_id=user.id, title='Reading', priority='low', category='other', due_date=today + timedelta(days=5))
        db.session.add_all([t_high, t_low])
        db.session.commit()

        plan = generate_study_schedule(user, daily_hours=2.0, days_ahead=7)
        assert plan['summary']['total_planned_hours'] > 0
        assert plan['summary']['total_tasks_scheduled'] >= 1
        assert len(plan['days']) == 7

        # Day 1 should prioritize t_high because it's high priority exam due soon
        day1 = plan['days'][0]
        assert day1['total_hours'] <= 2.0
        assert any(s['task_title'] == 'Exam Prep' for s in day1['sessions'])


def test_save_and_retrieve_study_plan_api(client, app, student):
    login(client)
    today = date.today()

    with app.app_context():
        user = db.session.get(User, student)
        t = Task(user_id=user.id, title='Math Assignment', priority='medium', category='assignment', due_date=today + timedelta(days=3))
        db.session.add(t)
        db.session.commit()

    # Generate plan via API
    res = client.post('/api/study-planner/generate', json={'daily_hours': 3.0, 'days_ahead': 5})
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['summary']['daily_study_hours'] == 3.0
    assert len(data['days']) == 5

    # Save plan via API
    res = client.post('/api/study-planner/save', json={'daily_hours': 2.0, 'days_ahead': 7})
    assert res.status_code == 201

    # Get saved plan via API
    res = client.get('/api/study-planner')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert len(data['sessions']) > 0
    first_session_id = data['sessions'][0]['id']
    assert data['sessions'][0]['completed'] is False

    # Toggle session completion
    res = client.post(f'/api/study-planner/sessions/{first_session_id}/toggle')
    assert res.status_code == 200
    assert res.get_json()['data']['completed'] is True

    # Clear sessions
    res = client.delete('/api/study-planner/sessions')
    assert res.status_code == 200

    res = client.get('/api/study-planner')
    assert len(res.get_json()['data']['sessions']) == 0


def test_session_scoping(client, app, student):
    user2_id = create_user(app, 'Other User', 'other@test.local')
    today = date.today()

    with app.app_context():
        s = StudySession(user_id=user2_id, title='Private Study', planned_date=today, duration_hours=2.0)
        db.session.add(s)
        db.session.commit()
        session_id = s.id

    login(client)
    # Student cannot toggle another user's session
    res = client.post(f'/api/study-planner/sessions/{session_id}/toggle')
    assert res.status_code == 404


def test_web_study_planner_flow(client, app, student):
    login(client)
    today = date.today()

    with app.app_context():
        user = db.session.get(User, student)
        t = Task(user_id=user.id, title='History Essay', priority='high', category='project', due_date=today + timedelta(days=4))
        db.session.add(t)
        db.session.commit()

    # Generate and save via form
    res = client.post('/study-planner/generate', data={
        'daily_hours': '2.0',
        'days_ahead': '7',
        'save_plan': 'true'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Study schedule generated' in res.data
    assert b'History Essay' in res.data

    # View study planner page
    res = client.get('/study-planner')
    assert res.status_code == 200
    assert b'Personal Study Planner' in res.data
    assert b'Total Planned Study' in res.data
