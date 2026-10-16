from tests.conftest import login
from app.models import Announcement, AnnouncementBookmark, User
from app.extensions import db

def test_announcement_bookmark_toggle_api(client, student, app):
    with app.app_context():
        a = Announcement(title='Campus Fest', content='Join us this Friday!', category='Event', priority='Normal')
        db.session.add(a)
        db.session.commit()
        a_id = a.id

    # Unauthenticated
    resp = client.post(f'/api/announcements/{a_id}/bookmark')
    assert resp.status_code == 401

    # Authenticated bookmark
    login(client)
    resp = client.post(f'/api/announcements/{a_id}/bookmark')
    assert resp.status_code == 201
    assert resp.get_json()['data']['bookmarked'] is True

    # Check in get_announcements API
    resp = client.get('/api/announcements')
    items = resp.get_json()['data']
    assert len(items) == 1
    assert items[0]['bookmarked'] is True

    # Toggle off (unbookmark)
    resp = client.post(f'/api/announcements/{a_id}/bookmark')
    assert resp.status_code == 200
    assert resp.get_json()['data']['bookmarked'] is False

    # Check in get_announcements API
    resp = client.get('/api/announcements')
    items = resp.get_json()['data']
    assert items[0]['bookmarked'] is False

def test_announcement_bookmark_scoping_and_filtering(client, student, admin, app):
    with app.app_context():
        a1 = Announcement(title='Exam Schedule', content='Finals start next week.', category='Exam', priority='Important')
        a2 = Announcement(title='Club Fair', content='Join student clubs.', category='Event', priority='Normal')
        db.session.add_all([a1, a2])
        db.session.commit()
        a1_id, a2_id = a1.id, a2.id

    # Student bookmarks a1
    login(client, 'student@test.local')
    client.post(f'/api/announcements/{a1_id}/bookmark')

    # Student filtered by bookmarked
    resp = client.get('/api/announcements?filter=bookmarked')
    data = resp.get_json()['data']
    assert len(data) == 1
    assert data[0]['id'] == a1_id

    # Web page filter
    resp = client.get('/announcements?filter=bookmarked')
    assert resp.status_code == 200
    assert b'Exam Schedule' in resp.data
    assert b'Club Fair' not in resp.data

    client.post('/logout')

    # Admin user should NOT see a1 as bookmarked
    login(client, 'admin@test.local')
    resp = client.get('/api/announcements')
    data = resp.get_json()['data']
    for item in data:
        assert item['bookmarked'] is False

    # Admin filter=bookmarked should be empty
    resp = client.get('/api/announcements?filter=bookmarked')
    assert len(resp.get_json()['data']) == 0

def test_announcement_bookmark_web_route(client, student, app):
    with app.app_context():
        a = Announcement(title='Workshop', content='Python workshop.', category='Academic', priority='Normal')
        db.session.add(a)
        db.session.commit()
        a_id = a.id

    login(client)
    resp = client.post(f'/announcements/{a_id}/bookmark', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Announcement bookmarked' in resp.data

    # Toggle off
    resp = client.post(f'/announcements/{a_id}/bookmark', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Bookmark removed' in resp.data
