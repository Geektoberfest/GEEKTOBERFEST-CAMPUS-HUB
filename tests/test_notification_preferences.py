from datetime import date, timedelta
from tests.conftest import login
from app.extensions import db
from app.models import Task, Announcement, Notification, NotificationPreference, User
from app.services.dashboard import generate_notifications


def test_get_notification_preferences_default(client, student):
    login(client)
    res = client.get('/api/notifications/preferences')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['notify_overdue'] is True
    assert data['notify_due_soon'] is True
    assert data['notify_announcements'] is True
    assert data['reminder_days_before'] == 1


def test_update_notification_preferences_api(client, app, student):
    login(client)
    res = client.put('/api/notifications/preferences', json={
        'notify_overdue': False,
        'notify_due_soon': True,
        'notify_announcements': False,
        'reminder_days_before': 3
    })
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['notify_overdue'] is False
    assert data['notify_due_soon'] is True
    assert data['notify_announcements'] is False
    assert data['reminder_days_before'] == 3

    # Check database persistence
    with app.app_context():
        user = db.session.get(User, student)
        prefs = user.get_notification_preferences()
        assert prefs.notify_overdue is False
        assert prefs.reminder_days_before == 3


def test_update_notification_preferences_validation(client, student):
    login(client)
    res = client.put('/api/notifications/preferences', json={
        'reminder_days_before': 0
    })
    assert res.status_code == 400

    res = client.put('/api/notifications/preferences', json={
        'reminder_days_before': 35
    })
    assert res.status_code == 400


def test_update_preferences_form(client, app, student):
    login(client)
    res = client.post('/notifications/preferences', data={
        'notify_due_soon': 'on',
        'reminder_days_before': '2'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Notification preferences updated' in res.data

    with app.app_context():
        user = db.session.get(User, student)
        prefs = user.get_notification_preferences()
        assert prefs.notify_overdue is False
        assert prefs.notify_due_soon is True
        assert prefs.notify_announcements is False
        assert prefs.reminder_days_before == 2


def test_notifications_generation_respects_preferences(client, app, student):
    login(client)
    today = date.today()

    with app.app_context():
        user = db.session.get(User, student)
        prefs = user.get_notification_preferences()
        prefs.notify_overdue = False
        prefs.notify_due_soon = True
        prefs.reminder_days_before = 2
        db.session.commit()

        # Create an overdue task, a task due in 2 days, and a task due tomorrow (1 day)
        t_overdue = Task(user_id=user.id, title='Overdue Homework', due_date=today - timedelta(days=2))
        t_due_2 = Task(user_id=user.id, title='Exam in 2 days', due_date=today + timedelta(days=2))
        t_due_1 = Task(user_id=user.id, title='Quiz tomorrow', due_date=today + timedelta(days=1))
        db.session.add_all([t_overdue, t_due_2, t_due_1])
        db.session.commit()

        generate_notifications(user)

        titles = [n.title for n in user.notifications]
        # Overdue notifications are disabled
        assert 'Task overdue' not in titles
        # Task due in 2 days should be triggered
        assert 'Task due in 2 days' in titles
        # Task due tomorrow should not be triggered (since reminder_days_before == 2)
        assert 'Task due tomorrow' not in titles


def test_notifications_page_renders_preferences(client, student):
    login(client)
    res = client.get('/notifications')
    assert res.status_code == 200
    assert b'Notification Preferences' in res.data
    assert b'Overdue task notifications' in res.data
    assert b'Reminder timing:' in res.data


def test_announcement_notifications_preference(client, app, student):
    login(client)
    today = date.today()

    with app.app_context():
        user = db.session.get(User, student)
        prefs = user.get_notification_preferences()
        prefs.notify_announcements = False
        db.session.commit()

        ann = Announcement(title='Important Update', content='Campus event today.')
        db.session.add(ann)
        db.session.commit()

        generate_notifications(user)
        assert not any(n.title == 'New Announcement' for n in user.notifications)

        prefs.notify_announcements = True
        db.session.commit()

        generate_notifications(user)
        assert any(n.title == 'New Announcement' for n in user.notifications)


def test_preferences_unauthorized(client):
    res = client.get('/api/notifications/preferences')
    assert res.status_code == 401

    res = client.put('/api/notifications/preferences', json={'notify_overdue': False})
    assert res.status_code == 401

    res = client.post('/notifications/preferences', data={'reminder_days_before': '2'})
    assert res.status_code == 302

