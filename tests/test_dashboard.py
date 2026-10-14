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

def test_consistent_date_formatting(client,student):
    login(client)
    client.post('/api/tasks', json={'title':'Exam Task','due_date':'2030-05-15','priority':'high','category':'exam'})
    # Check dashboard renders consistent DD Mon YYYY format
    res = client.get('/dashboard')
    assert res.status_code == 200
    assert b'15 May 2030' in res.data
    # Check deadlines renders consistent DD Mon YYYY format
    dl_res = client.get('/deadlines')
    assert dl_res.status_code == 200
    assert b'15 May 2030' in dl_res.data
    # Check tasks.js contains formatDisplayDate
    js_res = client.get('/static/js/tasks.js')
    assert js_res.status_code == 200
    assert b'formatDisplayDate' in js_res.data
