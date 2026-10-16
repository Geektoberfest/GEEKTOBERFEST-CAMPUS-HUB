from tests.conftest import login
from app.models import Resource
from app.extensions import db

def test_resource_detail_view(client, student, app):
    with app.app_context():
        res = Resource(
            title='Flask Documentation',
            description='Official documentation for Flask framework.',
            subject='Web Development',
            resource_type='Documentation',
            url='https://flask.palletsprojects.com/'
        )
        db.session.add(res)
        db.session.commit()
        res_id = res.id

    # Unauthenticated redirect
    resp = client.get(f'/resources/{res_id}')
    assert resp.status_code == 302

    # Authenticated access
    login(client)
    resp = client.get(f'/resources/{res_id}')
    assert resp.status_code == 200
    assert b'Flask Documentation' in resp.data
    assert b'Official documentation for Flask framework.' in resp.data
    assert b'Web Development' in resp.data
    assert b'Documentation' in resp.data
    assert b'https://flask.palletsprojects.com/' in resp.data

    # Not found
    resp = client.get('/resources/9999')
    assert resp.status_code == 404

def test_resource_api_single(client, student, app):
    with app.app_context():
        res = Resource(
            title='Python Tutorial',
            description='Beginner Python guides.',
            subject='Programming',
            resource_type='Website',
            url='https://docs.python.org/3/tutorial/'
        )
        db.session.add(res)
        db.session.commit()
        res_id = res.id

    # Unauthenticated API
    resp = client.get(f'/api/resources/{res_id}')
    assert resp.status_code == 401

    # Authenticated API
    login(client)
    resp = client.get(f'/api/resources/{res_id}')
    assert resp.status_code == 200
    data = resp.get_json()['data']
    assert data['id'] == res_id
    assert data['title'] == 'Python Tutorial'
    assert data['resource_type'] == 'Website'
    assert data['subject'] == 'Programming'
    assert data['url'] == 'https://docs.python.org/3/tutorial/'

    # Not found API
    resp = client.get('/api/resources/9999')
    assert resp.status_code == 404

def test_resources_list_links_to_detail(client, student, app):
    with app.app_context():
        res = Resource(
            title='FastAPI Guide',
            description='Modern async web framework.',
            subject='Python',
            resource_type='Course',
            url='https://fastapi.tiangolo.com/'
        )
        db.session.add(res)
        db.session.commit()
        res_id = res.id

    login(client)
    resp = client.get('/resources')
    assert resp.status_code == 200
    assert f'/resources/{res_id}'.encode() in resp.data
