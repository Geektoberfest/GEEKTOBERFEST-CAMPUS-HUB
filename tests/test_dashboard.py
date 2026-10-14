from tests.conftest import login

def test_dashboard_stats(client,student):
    login(client);client.post('/api/tasks',json={'title':'One','completed':False});client.post('/api/tasks',json={'title':'Two'})
    data=client.get('/api/dashboard').get_json()['data'];assert data['total']==2;assert data['pending']==2;assert data['completed']==0;assert data['productivity']==0

def test_notification_relative_timestamps(client,student,app):
    from datetime import datetime, timedelta
    from app.extensions import db
    from app.models import Notification
    login(client)
    with app.app_context():
        n = Notification(user_id=student, title='Reminder', message='Check homework', created_at=datetime.now() - timedelta(hours=2))
        db.session.add(n)
        db.session.commit()
    res = client.get('/notifications')
    assert res.status_code == 200
    assert b'2 hours ago' in res.data

def test_back_to_top_control(client,student):
    login(client)
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b'id="backToTop"' in res.data
    assert b'aria-label="Back to top"' in res.data
    js_res = client.get('/static/js/app.js')
    assert js_res.status_code == 200
    assert b'backToTop' in js_res.data
    css_res = client.get('/static/css/style.css')
    assert css_res.status_code == 200
    assert b'back-to-top' in css_res.data

def test_dashboard_period_selection_api(client, student):
    from datetime import date, timedelta
    login(client)
    data7 = client.get('/api/dashboard').get_json()['data']
    assert data7['period'] == '7d'
    assert len(data7['daily']) == 7

    data14 = client.get('/api/dashboard?period=14d').get_json()['data']
    assert data14['period'] == '14d'
    assert len(data14['daily']) == 14

    data30 = client.get('/api/dashboard?period=30d').get_json()['data']
    assert data30['period'] == '30d'
    assert len(data30['daily']) == 30

    data_month = client.get('/api/dashboard?period=month').get_json()['data']
    assert data_month['period'] == 'month'
    today = date.today()
    assert len(data_month['daily']) == today.day

    start = (today - timedelta(days=5)).isoformat()
    end = today.isoformat()
    data_custom = client.get(f'/api/dashboard?start_date={start}&end_date={end}').get_json()['data']
    assert data_custom['period'] == 'custom'
    assert len(data_custom['daily']) == 6

def test_dashboard_web_date_range(client, student):
    login(client)
    resp = client.get('/dashboard?period=14d')
    assert resp.status_code == 200
    assert b'Last 14 days' in resp.data
    assert b'selected' in resp.data

def test_mark_all_notifications_read(client,student,admin,app):
    from app.extensions import db
    from app.models import Notification
    with app.app_context():
        n1 = Notification(user_id=student, title='Alert 1', message='First', read=False)
        n2 = Notification(user_id=student, title='Alert 2', message='Second', read=False)
        n3 = Notification(user_id=admin, title='Admin Alert', message='Admin message', read=False)
        db.session.add_all([n1, n2, n3])
        db.session.commit()
        n1_id, n2_id, n3_id = n1.id, n2.id, n3.id

    login(client)
    res = client.post('/notifications/mark-all-read', follow_redirects=True)
    assert res.status_code == 200
    assert b'All notifications marked as read.' in res.data

    with app.app_context():
        assert db.session.get(Notification, n1_id).read is True
        assert db.session.get(Notification, n2_id).read is True
        # Scoping check: admin's notification was NOT marked as read
        assert db.session.get(Notification, n3_id).read is False

    # Also test API endpoint
    api_res = client.post('/api/notifications/mark-all-read')
    assert api_res.status_code == 200
    assert api_res.get_json()['success'] is True
